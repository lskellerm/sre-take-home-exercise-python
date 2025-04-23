# Fetch Rewards - Endpoint availability Monitoring

Command line utility script to monitor the availability and response time of a set of endpoints. The script will check the endpoints at regular intervals of 15s and log the results, calculating the availability percentage for each domain.

Completed as part of the Fetch Rewards Site Reliability Engineering take-home exercise.

## 1. Specification Requirements
- Must accept a YAML configuration file as a command-line argument.
- YAML format must match that in the provided sample.
- Must accurately determine the availability of all endpoints during every check cycle.o
- Endpoints are only considered available if they meet the conditions:
  - HTTP status code is between 200 and 299
  - Response time is less than 500ms
- Must ignore port numbers when determining domains
- Must determine availability cumulatively 
- Check cycles should run every 15 seconds, regardless of the number of endpoints and their response times.


## Installing and running the Code
  1. Clone the repository:
        ```bash
        git clone https://github.com/lskellerm/sre-take-home-exercise-python.git

        cd sre-take-home-exercise-python
        ```
  2. Create a virtual environment (optional but recommended):
        ```bash
        python -m venv venv

        # Activate the virtual environment

        # macOS/Linux
        source venv/bin/activate

        # Windows
        venv\Scripts\activate
        ```
  3. Install the required packages:
     ```bash
      pip install -r requirements.txt
      ```
  4. Run the script:
      ```bash
       python main.py sample.yaml
       python main.py custom_endpoints.yaml
       ```

      Logs will be written to `/endpoint_monitor_logs` and also written to stdout.

## Bugs and Issues Identified in the Original Implementation
1. _**No Default HTTP method**_
   - The original code does not specify a default HTTP method for requests when the method is not provided in the YAML file. 
   - <u>Fix:</u> Assigned a default value for the HTTP method to "GET" if not specified in the YAML file, as per the requirements.
2. _**Missing name handling**_
      - The original implementation does not handle the case where the 'free-text name' of the endpoint is not provided in the YAML file. Per the requirements, the name key is required.
      - <u>Fix:</u> Assigned a default value for the name to "unknown" if not specified in the YAML file and logged a warning message.
3. _**Missing URL handling**_
      - No validation is performed on the URL format in the original code. If the URL is not valid, the script will fail when trying to make a request.
      - <u>Fix:</u> Added a check to ensure that the URL is valid before making a request. If the URL is invalid, log the error and mark the endpoint as unavailable.
4. _**Missing timeout handling**_
      - The original code does not explicitly handle timeouts when making requests. If a request takes too long, it may hang indefinitely.
      - <u>Fix:</u> Added a timeout parameter to the http client request method to ensure that the request times out after the specified duration (500ms).
5. _**Incorrect enforcement of 15s interval**_
      - The original code does not enforce the 15-second interval between checks. It wasn't ensuring the correct timing between checks.
      - <u>Fix:</u> Calculated how much time    has passed since the last check and adjusted the sleep time accordingly to ensure that each check occurs every 15 seconds.

6. _**Not extracting port numbers from the endpoint**_
      - Port numbers were not being extracted from the url key in the yaml configuration.
      - <u>Fix:</u> Parsed out the port number from the URL using `urlparse` and used it to determine the domain name correctly, ensuring proper per-domain availability calculations.

## Enhancements and Improvements
1. _**Logging**_
   - The original code does not log the results of the checks. It only prints them to the console.
   - <u>Fix:</u> Added structured and unified logging functionality to log the results of each check to a log file and also the console. 
2. _**Performance**_
   - The original code checks each endpoint sequentially, which can be slow if there are many endpoints, and may result in the 15s not being enforced.  
   - <u>Fix:</u> Implemented asynchronous requests using the `aiohttp` library to check multiple endpoints concurrently, improving performance and reducing overall check time.
3. _**Error Handling**_
      - Improved error handling by explicitly logging timeout and exception reasons throughout the code.
4. _**Strongly typed**_
   - Added type annotations to functions and methods to provide better clarity and improve dx.
   - Created TypeDict for Endpoint to ensure keys in the YAML file are correctly typed and validated.