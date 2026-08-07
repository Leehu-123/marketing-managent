import sys

log_file = r"C:\Users\Admin\.gemini\antigravity\brain\0b45219c-2a7a-46ac-972f-ceb21d667e32\.system_generated\tasks\task-912.log"

try:
    with open(log_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if "[AI ERROR]" in line:
                print(f"Line {i+1}: {line.strip()}")
except Exception as e:
    print(f"Error: {e}")
