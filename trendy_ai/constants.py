import os


DATA_SIZE = 30


def model_path():
    current_directory = trendy_ai_dir()
    return os.path.join(current_directory, 'ffnn/trendy_model.pth')


def trendy_ai_dir():
    current_file_path = os.path.realpath(__file__)
    current_directory = os.path.dirname(current_file_path)
    return current_directory
