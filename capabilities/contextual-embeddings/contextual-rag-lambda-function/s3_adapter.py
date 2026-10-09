import json

import boto3
from botocore.exceptions import ClientError


class S3Adapter:
    def __init__(self):
        # S3 client 생성
        self.s3_client = boto3.client("s3")

    def write_output_to_s3(self, bucket_name, file_name, json_data):
        """
        S3 bucket에 JSON object를 기록합니다

        :param bucket_name: S3 bucket 이름
        :param file_name: Bucket에 생성할 파일 이름
        :param json_data: 기록할 JSON object
        :return: 파일이 업로드되면 True, 그렇지 않으면 False
        """

        try:
            # JSON object를 문자열로 변환
            json_string = json.dumps(json_data)

            # 파일 업로드
            response = self.s3_client.put_object(
                Bucket=bucket_name, Key=file_name, Body=json_string, ContentType="application/json"
            )

            # 업로드 성공 여부 확인
            if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                print(f"Successfully uploaded {file_name} to {bucket_name}")
                return True
            else:
                print(f"Failed to upload {file_name} to {bucket_name}")
                return False

        except ClientError as e:
            print(f"Error occurred: {e}")
            return False

    def read_from_s3(self, bucket_name, file_name):
        """
        S3 bucket에 JSON object를 기록합니다

        :param bucket_name: S3 bucket 이름
        :param file_name: Bucket에 생성할 파일 이름
        :return: 파일이 업로드되면 True, 그렇지 않으면 False
        """
        try:
            # S3에서 object 조회
            response = self.s3_client.get_object(Bucket=bucket_name, Key=file_name)

            # 파일 내용 읽기
            return json.loads(response["Body"].read().decode("utf-8"))

        except ClientError as e:
            print(f"Error reading file from S3: {str(e)}")

    def parse_s3_path(self, s3_path):
        # 's3://' prefix가 있으면 제거
        s3_path = s3_path.replace("s3://", "")

        # 경로를 bucket 및 key로 분리
        parts = s3_path.split("/", 1)

        if len(parts) != 2:
            raise ValueError("Invalid S3 path format")

        bucket_name = parts[0]
        file_key = parts[1]

        return bucket_name, file_key
