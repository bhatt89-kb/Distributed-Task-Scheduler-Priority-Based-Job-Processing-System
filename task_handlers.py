import time


def execute_task(task_name):

    if task_name == "send_email":
        print("Sending email...")
        time.sleep(2)
        return "Email sent"

    elif task_name == "generate_report":
        print("Generating report...")
        time.sleep(4)
        return "Report generated"

    elif task_name == "resize_image":
        print("Resizing image...")
        time.sleep(3)
        return "Image resized"

    elif task_name == "fail_task":
        print("Simulating task failure...")
        raise Exception("Something went wrong!")

    else:
        print(f"Unknown task: {task_name}")
        return "Unknown task"