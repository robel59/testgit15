import os
import sys
import shutil
import random
import string
import subprocess

def generate_random_string(length):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def copy_website(destination_folder, unique_name):
    project_folder_path = os.path.join(destination_folder, unique_name)
    #source_folder = os.path.join(os.getcwd(), 'website')
    source_folder = '/Users/admin/Documents/website_project/unice_django/server/convert/websit'

    if not os.path.exists(source_folder):
        raise FileNotFoundError(f"Source folder '{source_folder}' does not exist.")
    shutil.copytree(source_folder, project_folder_path)


def copy_non_html_files(source_folder, destination_folder):
    for item in os.listdir(source_folder):
        item_path = os.path.join(source_folder, item)
        if os.path.isfile(item_path) and not item.endswith('.html'):
            shutil.copy2(item_path, destination_folder)
        elif os.path.isdir(item_path):
            new_destination_folder = os.path.join(destination_folder, item)
            if not os.path.exists(new_destination_folder):
                os.mkdir(new_destination_folder)
            copy_non_html_files(item_path, new_destination_folder)

def find_index_html(folder_path):
    for root, dirs, files in os.walk(folder_path):
        if 'index.html' in files:
            return os.path.join(root, 'index.html')
    return None

def main():
    if len(sys.argv) != 2:
        print("Usage: python copy_website.py folder_name")
        return

    folder_name = sys.argv[1]
    current_directory = '/Users/admin/Documents/website_project/unice_django/server/convert'#os.getcwd()
    destination_folder = '/Users/admin/Documents/website_project/unice_django/server/convert/project'

    #destination_folder = os.path.join(current_directory, 'project')
    
    # Generate a unique name using folder_name and a random string
    random_string = generate_random_string(8)  # Adjust the length as needed
    unique_name = f"{random_string}"

    copy_website(destination_folder, unique_name)
    destination_folder2 = os.path.join(destination_folder, unique_name,'convert.py')

    project_static_folder = os.path.join(destination_folder, unique_name, 'static')
    source_folder = os.path.join(current_directory, folder_name)
    copy_non_html_files(source_folder, project_static_folder)

    index_html_path = find_index_html(source_folder)
    if index_html_path:
        print(f"Found index.html at: {index_html_path}")
        print("DDD")
        print(source_folder)
        print("EEEE")
        print(index_html_path)
        subprocess.run(['python3', destination_folder2, index_html_path])#, str(source_folder)])
        print("WWWWW")
    else:
        print("No index.html found in the specified folder.")

if __name__ == "__main__":
    main()
