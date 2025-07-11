import os
import platform
import subprocess
from datetime import datetime
from google import genai
from google.genai import types

GOOGLE_API_KEY = "your-key-here"
client = genai.Client(api_key=GOOGLE_API_KEY)

SESSION_FILE = "session.log"

def log_to_file(text):
    with open(SESSION_FILE, "a") as f:
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        f.write(f"{timestamp} {text}\n")

def execute_command(command: str) -> str:
    try:
        system = platform.system()
        if system == "Windows":
            result = subprocess.run(["cmd", "/c", command], capture_output=True, text=True)
        else:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)

        if result.stderr:
            return f"Error: {result.stderr.strip()}"
        return f"Success: {result.stdout.strip() or 'Command executed successfully.'}"
    except Exception as e:
        return f"Exception: {str(e)}"

# ✨ Auto-write any code to proper file based on language
def write_files_from_text(text):
    import re

    code_blocks = re.findall(r"```(\w+)?\n(.*?)```", text, re.DOTALL)

    if not code_blocks:
        return write_files_by_keyword(text)

    saved = []
    for lang, code in code_blocks:
        lang = lang.strip().lower()

        filename = {
            "python": "main.py",
            "py": "main.py",
            "javascript": "script.js",
            "js": "script.js",
            "typescript": "script.ts",
            "ts": "script.ts",
            "java": "App.java",
            "c": "main.c",
            "cpp": "main.cpp",
            "html": "index.html",
            "css": "style.css",
            "json": "data.json",
            "go": "main.go",
            "php": "index.php",
            "ruby": "main.rb",
            "swift": "main.swift",
            "rs": "main.rs",
            "kotlin": "main.kt",
            "sh": "script.sh",
            "bash": "script.sh",
        }.get(lang, f"snippet.{lang if lang else 'txt'}")

        status = append_or_create(filename, code)
        saved.append(status)

    return "\n".join(saved)

# Handle plain HTML/CSS/JS if no code block syntax is used
def write_files_by_keyword(text):
    if "<!DOCTYPE html>" in text or "<html" in text:
        return append_or_create("index.html", text, insert_marker="</body>")
    elif "{" in text and "}" in text and "body" in text:
        return append_or_create("style.css", text)
    elif "function" in text or "console.log" in text:
        return append_or_create("script.js", text)
    return ""

def append_or_create(filename, content, insert_marker=None):
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            f.write(content)
        return f"Created {filename}"

    with open(filename, "r") as f:
        existing = f.read()

    if insert_marker and insert_marker in existing:
        updated = existing.replace(insert_marker, content + "\n" + insert_marker)
    else:
        updated = existing + "\n\n" + content

    with open(filename, "w") as f:
        f.write(updated)

    return f"Updated {filename}"

execute_command_declaration = {
    "name": "executeCommand",
    "description": "Execute a terminal/shell command (e.g., mkdir, touch, echo, etc).",
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The terminal command to run. Example: mkdir myproject",
            }
        },
        "required": ["command"]
    }
}

tools = [types.Tool(function_declarations=[execute_command_declaration])]
config = types.GenerateContentConfig(
    tools=tools,
    system_instruction=(
        "You are a website builder. You write and update files in various programming languages. "
        "Use code blocks with language hints (e.g., ```python) when responding with code. "
        "Use the executeCommand tool for shell tasks. If a file already exists, append or modify it."

        "current user operating system is: {platform.system()}"

        "<---What is your role?--->"
        "1:Analyze the user's request and determine if it requires code generation or file updates."
        "2:Generate the necessary code snippets or file changes based on the analysis."
        "3:Provide clear and concise explanations for the generated code."
        "4:Use the executeCommand tool for any shell commands needed to create or modify files." 
        "5:Give user command step by step"

        "Now you can give user command:"
        "1:First create folder"
        "2:Then create files in that folder requied for the project, ex- index.html, style.css, script.js, etc."
        "3:Then write code in those files, ex- html, css, js, python, etc."
        "4:Exectute all the commands step by step in one go."
        "5:If you need to run any command, use the executeCommand tool."
        "6:Add the code right after makig the file, do not just create empty files."

        "if making a website create the html,css and javascript files, if making a python project create the python files, if making a java project create the java files, etc."
        "Also write all the required codes in the files, do not just create empty files."

        "If there is any error and user point it out, make changes in the required, fix it automatically"
        "Always make good looking css, dont just make simple looking website"
        

    )
)

available_tools = {
    "executeCommand": lambda args: execute_command(args["command"])
}

history = []

def run_agent(user_input: str):
    history.append(types.Content(role="user", parts=[types.Part(text=user_input)]))
    log_to_file(f"User: {user_input}")

    while True:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=history,
            config=config,
        )

        parts = response.candidates[0].content.parts
        first_part = parts[0]
        func_call = getattr(first_part, "function_call", None)

        if func_call and func_call.name and func_call.args:
            name = func_call.name
            args = func_call.args
            print(f"\nFunction to call: {name}")
            print(f"Args: {args}")

            result = available_tools.get(name, lambda _: "Unknown tool")(args)
            print(f"Result: {result}")
            log_to_file(f"Tool: {name}, Args: {args}, Result: {result}")

            history.append(types.Content(role="model", parts=[types.Part(function_call=func_call)]))
            history.append(types.Content(role="user", parts=[
                types.Part(function_response={"name": name, "response": {"result": result}})
            ]))
        else:
            response_text = first_part.text
            print(f"\nGemini: {response_text}")
            log_to_file(f"Gemini: {response_text}")

            file_status = write_files_from_text(response_text)
            if file_status:
                print(file_status)
                log_to_file(file_status)

            history.append(types.Content(role="model", parts=[types.Part(text=response_text)]))
            break

def main():
    print(f"Website Builder Agent Ready (OS: {platform.system()})")
    while True:
        try:
            user_input = input("\nAsk me anything --> ")
            if user_input.lower() in ["exit", "quit"]:
                print("Exiting.")
                break
            run_agent(user_input)
        except KeyboardInterrupt:
            print("\nExiting.")
            break

if __name__ == "__main__":
    main()