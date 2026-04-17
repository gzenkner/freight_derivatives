# test_try_except_raise.py

# SECTION: SUCCESS CASE
def api_call_success():
    print("\n--- success case ---")

    try:
        print("inside try: making fake API call")
        response = {"status_code": 200, "data": {"message": "ok"}}

        if response["status_code"] != 200:
            raise ValueError("non-200 response")

        print("inside try: API call succeeded")
        return response["data"]

    except Exception as e:
        print("inside except: caught an error")
        raise RuntimeError(f"API call failed: {e}") from e


# SECTION: FAILURE CASE
def api_call_failure():
    print("\n--- failure case ---")

    try:
        print("inside try: making fake API call")
        response = {"status_code": 500, "data": None}

        if response["status_code"] != 200:
            raise ValueError(f"non-200 response: {response['status_code']}")

        print("inside try: API call succeeded")
        return response["data"]

    except Exception as e:
        print("inside except: caught an error")
        print("inside except: about to raise RuntimeError")
        raise RuntimeError(f"API call failed: {e}") from e


# SECTION: MAIN TESTS
def main():
    print("starting tests")

    # success test
    try:
        result = api_call_success()
        print(f"success function returned: {result}")
    except Exception as e:
        print(f"outer catch for success case: {type(e).__name__}: {e}")

    # # failure test
    # try:
    #     result = api_call_failure()
    #     print(f"failure function returned: {result}")
    # except Exception as e:
    #     print(f"outer catch for failure case: {type(e).__name__}: {e}")

    # print("\nfinished tests")


if __name__ == "__main__":
    main()