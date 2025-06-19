import subprocess
import os
import tempfile
from typing import Tuple, Optional

def run_script(script_content: str, env_vars: dict, success_keyword: Optional[str] = None) -> Tuple[bool, str]:
    """
    Runs a script and captures its output, with a flexible success condition.

    Args:
        script_content: The Python code to execute.
        env_vars: A dictionary of environment variables.
        success_keyword: If provided, the script's stdout must contain this keyword for success.
                         If None, only the exit code is checked.

    Returns:
        A tuple of (success: bool, logs: str).
    """
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.py', encoding='utf-8') as script_file:
        script_file.write(script_content)
        script_path = script_file.name

    script_env = os.environ.copy()
    script_env.update(env_vars)
    logs = ""
    success = False

    try:
        process = subprocess.run(
            ['python', script_path],
            env=script_env,
            capture_output=True,
            text=True,
            timeout=120
        )
        stdout = process.stdout
        stderr = process.stderr
        logs = f"--- STDOUT ---\n{stdout}\n--- STDERR ---\n{stderr}"

        # Determine success
        if process.returncode == 0:
            if success_keyword:
                # Success requires the keyword in stdout
                if success_keyword in stdout.strip().split('\n'):
                    success = True
                else:
                    logs += f"\n--- SYSTEM ---\nScript finished, but '{success_keyword}' keyword was not found."
            else:
                # Success is just a zero exit code
                success = True
        else:
            logs += f"\n--- SYSTEM ---\nScript failed with exit code: {process.returncode}"

    except subprocess.TimeoutExpired:
        logs = "--- SYSTEM ---\nScript execution timed out after 2 minutes."
    except Exception as e:
        logs = f"--- SYSTEM ---\nAn unexpected error occurred: {e}"
    finally:
        os.remove(script_path)

    return success, logs