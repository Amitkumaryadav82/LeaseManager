import boto3
import os

bucket_name = 'capleasemanager'
s3_faiss = 'faiss/'

def rename_and_upload_files():
    print("Starting to rename and upload files from /tmp directories")
    try:
        s3 = boto3.client('s3')
        base_dir = '/tmp'
        
        for directory in os.listdir(base_dir):
            dir_path = os.path.join(base_dir, directory)
            if os.path.isdir(dir_path) and directory.startswith('faiss_index_'):
                index_id = directory.split('_')[-1].strip()
                for file in os.listdir(dir_path):
                    file_path = os.path.join(dir_path, file)
                    file_extension = file.split('.')[-1]
                    new_file_name = f"index_{index_id}.{file_extension}"
                    s3_key = f'{s3_faiss}{new_file_name}'
                    print(f"Uploading {file_path} to S3 at {s3_key}")
                    with open(file_path, 'rb') as f:
                        s3.put_object(Bucket=bucket_name, Key=s3_key, Body=f.read())
        print("Completed renaming and uploading files from /tmp directories")
    except Exception as e:
        print(f"Error renaming and uploading files: {e}")


# Call the function to rename and upload files
if __name__ == "__main__":
    rename_and_upload_files()