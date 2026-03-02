"""Safe Python code execution in a subprocess with timeout."""
import os
import subprocess
import sys
import tempfile

TIMEOUT_SECONDS = 15
MAX_OUTPUT_LENGTH = 3000


def execute_python(code: str) -> str:
    """
    Execute Python code in an isolated subprocess.

    Returns stdout on success, or stderr on failure.
    Enforces a 15-second timeout and 3000-char output limit.
    """
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".py", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            tmp_path = f.name

        result = subprocess.run(
            [sys.executable, "-u", tmp_path],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )

        stdout = result.stdout[:MAX_OUTPUT_LENGTH]
        stderr = result.stderr[:MAX_OUTPUT_LENGTH]

        if result.returncode == 0:
            return (
                stdout.strip()
                if stdout.strip()
                else "✅ Code executed successfully (no output)"
            )

        parts = []
        if stdout.strip():
            parts.append(f"Output:\n{stdout.strip()}")
        if stderr.strip():
            parts.append(f"Error:\n{stderr.strip()}")
        return "\n\n".join(parts) or "Code exited with non-zero status"

    except subprocess.TimeoutExpired:
        return f"⏱️ Execution timed out ({TIMEOUT_SECONDS}s limit exceeded)"
    except Exception as e:
        return f"❌ Execution error: {str(e)}"
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
