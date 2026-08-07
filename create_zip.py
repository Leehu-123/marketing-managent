import os
import zipfile

def create_zip(source_dir, output_zip, exclude_dirs, exclude_exts):
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Exclude directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
            for file in files:
                if any(file.endswith(ext) for ext in exclude_exts):
                    continue
                if file.startswith('.'):
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname)

if __name__ == "__main__":
    base_dir = r"d:\Antigrapvity\Marketing manager"
    
    # Zip backend
    backend_dir = os.path.join(base_dir, "backend")
    backend_zip = os.path.join(base_dir, "backend_deploy.zip")
    create_zip(
        backend_dir, 
        backend_zip, 
        exclude_dirs=['venv', '__pycache__'], 
        exclude_exts=['.db', '.db-journal']
    )
    print(f"Created {backend_zip}")

    # Zip client_automation
    client_dir = os.path.join(base_dir, "client_automation")
    client_zip = os.path.join(base_dir, "client_automation_deploy.zip")
    create_zip(
        client_dir, 
        client_zip, 
        exclude_dirs=['venv', '__pycache__'], 
        exclude_exts=['.db', '.db-journal', '.png', '.mp4']
    )
    print(f"Created {client_zip}")
