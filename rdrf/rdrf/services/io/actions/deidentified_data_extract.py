def execute(custom_action, user):
    if not security_check(user):
        raise Exception("not allowed")
    if custom_action.run_async:
        task_id = extract_data.delay(user)
