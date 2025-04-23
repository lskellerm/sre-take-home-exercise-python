import yaml
import time
import os
import logging
import sys

from aiohttp import ClientSession, ClientTimeout
from asyncio import gather, TimeoutError, sleep
from collections import defaultdict
from typing import Any, Literal, TypedDict, Union
from typing import Coroutine as CoroutineType
from urllib.parse import urlparse, ParseResult
from datetime import datetime


class Endpoint(TypedDict):
    """A dictionary representing an endpoint configuration."""

    name: str
    url: str
    method: str
    headers: Union[dict[str, Any], None]
    body: Union[dict[str, Any], None]


# Configure logging, stored in the endpoint_monitor_logs directory
def configure_logging() -> logging.Logger:
    """Configure logging for the application."""

    log_dir: str = "endpoint_monitor_logs"
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    log_file: str = os.path.join(
        log_dir, f"{datetime.now().strftime('%Y%m%d')}_endpoint_monitoring.log"
    )

    # Set up the logging format and handlers
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(log_file)
    stdout_handler = logging.StreamHandler(sys.stdout)
    log_formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    # Set the formatter for both handlers
    file_handler.setFormatter(log_formatter)
    stdout_handler.setFormatter(log_formatter)

    # Attach the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(stdout_handler)

    return logger


logger = configure_logging()


# Function to load configuration from the YAML file
def load_config(file_path: str) -> Any:
    with open(file_path, "r") as file:
        return yaml.safe_load(file)


# Function to perform health checks
async def check_health(
    endpoint: Endpoint, session: ClientSession
) -> tuple[str, Literal["UP", "DOWN"]]:
    name: str = endpoint.get("name", "unknown")  # Provide default to ensure str type
    url: Union[str, None] = endpoint.get("url")

    if not name:  # The free-text name describing the endpoint wasn't being checked, required as per specifications
        logger.warning(f"Missing name to describe the HTTP endpoint for: {endpoint}")
        name = "unknown"

    if not url:  # Handle case where URL is not provided
        logger.error(f"Missing URL for the HTTP endpoint: {endpoint}")
        return (name, "DOWN")

    method: str = endpoint.get(
        "method",
        "GET",  # The default is GET when omitted, as per requirement
    )
    headers: Union[dict[str, Any], None] = endpoint.get("headers")
    body: Union[dict[str, Any], None] = endpoint.get("body")

    try:
        async with (
            session.request(
                method,
                url,
                headers=headers,
                json=body,
                timeout=ClientTimeout(
                    total=0.5  # 500ms timeout as per requirement: For endpoint to be considered 'available'
                ),
            ) as response
        ):
            if 200 <= response.status < 300:
                return name, "UP"
            else:
                return name, "DOWN"
    except TimeoutError:  # Added explicit checks for timeout, providing more insight as to reason for unavailability
        logger.error(f"Request to {name} timed out, {url} is DOWN")

        return name, "DOWN"
    except Exception as e:
        logger.error(f"Request to {name} failed, {url} is DOWN: {str(e)}")
        return name, "DOWN"


# Main function to monitor endpoints
async def monitor_endpoints(file_path: str) -> None:
    config: Any = load_config(file_path)
    domain_stats: defaultdict[str, dict[str, int]] = defaultdict(
        lambda: {"up": 0, "total": 0}
    )

    # Initialize the aiohttp session for making concurrent requests
    async with ClientSession() as session:
        while True:
            check_cycle_start: float = (
                time.time()  # Record the time the check cycle started
            )
            logger.info("Starting health check cycle...")

            # Create list of tasks for concurrent execution of the health checks, allowing multiple endpoints to be checked concurrently
            tasks: list[CoroutineType[Any, Any, tuple[str, Literal["UP", "DOWN"]]]] = []
            for endpoint in config:
                tasks.append(check_health(endpoint, session))

            # Wait for all requests to complete
            results: list[tuple[str, Literal["UP", "DOWN"]]] = await gather(*tasks)

            # Keep track of the number of unique domains checked this cycle
            domains_this_cycle: set[str] = set()

            # Process the results for each endpoint
            for endpoint, (_, status) in zip(config, results):
                url = endpoint.get("url", "")
                if url:
                    parsed_url: ParseResult = urlparse(url)
                    domain = parsed_url.netloc.split(":")[0]
                    domains_this_cycle.add(domain)

                    logger.info(f"{domain} is {status}")
                    domain_stats[domain]["total"] += 1
                    if status == "UP":
                        domain_stats[domain]["up"] += 1

            logger.info(
                f"\n\nQueried {len(tasks)} endpoints across {len(domains_this_cycle)} unique domain(s) this cycle\n"
            )

            # Log cumulative availability percentages
            for domain, stats in domain_stats.items():
                availability: int = round(100 * stats["up"] / stats["total"])
                logger.info(f"{domain} has {availability}% availability percentage")

            logger.info("\n" + "---" * 50)

            # Calculate the time taken for the check cycle to determine how long to sleep to meet the 15s requirement
            time_elapsed: float = time.time() - check_cycle_start

            # Sleep for the remaining time to ensure a 15-second interval
            sleep_time: float = max(0, 15 - time_elapsed)
            await sleep(sleep_time)


# Entry point of the program
if __name__ == "__main__":
    import sys
    import asyncio

    if len(sys.argv) != 2:
        print("Usage: python monitor.py <config_file_path>")
        sys.exit(1)

    config_file: str = sys.argv[1]
    try:
        asyncio.run(monitor_endpoints(config_file))
    except KeyboardInterrupt:
        logger.info("\nMonitoring stopped by user.")
