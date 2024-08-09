
import os
'''
#Messing around with functions to make things more legible
'''
def crawl_source_shorten_titles(path):

    # List files in directory
    for file_name in os.listdir(path):

        # Build path to file
        file_path = os.path.join(path, file_name)

        # Recursively crawl to next directory level
        if os.path.isdir(file_path):
            crawl_source_shorten_titles(file_path)

        # Modify .rst source file title
        else:
            full_name, extension = os.path.splitext(file_path)
            if extension == ".rst":

                # Read file, modify title, write back to file
                with open(file_path, 'r') as file:
                    lines = file.readlines()
                lines[0] = lines[0].split('.')[-1]
                lines[1] = ('=' * (len(lines[0]) - 1 )) + '\n'
                with open(file_path, 'w') as file:
                    file.writelines(lines)
                bad_words = ["custom", "index", "search"]
                if all(word not in full_name for word in bad_words):
                    os.rename(file_name, lines[0])



''' New Version'''
def new_shortener(path):
    for file_name in os.listdir(path):

        # Build path to file
        file_path = os.path.join(path, file_name)
        full_name, extension = os.path.splitext(file_path)

        with open(file_path, 'r') as file:
            lines = file.readlines()
        lines[0] = lines[0].split('.')[-1]
        lines[1] = ('=' * (len(lines[0]) - 1 )) + '\n'
        with open(file_path, 'w') as file:
            file.writelines(lines)
        bad_words = ["custom", "index", "search"]
        if all(word not in full_name for word in bad_words):
            os.rename(file_name, lines[0])

