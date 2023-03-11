import numpy as np
import cv2
import os
import boto3
import json

s3 = boto3.client('s3')

def remove_the_blackborder(source):
    #读取图片
    image = cv2.imread(source)
    #中值滤波，去除黑色边际中可能含有的噪声干扰
    img = cv2.medianBlur(image, 5)
    #调整裁剪效果
    b = cv2.threshold(img, 3, 255, cv2.THRESH_BINARY)
    #二值图--具有三通道
    binary_image = b[1]
    binary_image = cv2.cvtColor(binary_image,cv2.COLOR_BGR2GRAY)
 
    edges_y, edges_x = np.where(binary_image==255)
    bottom = min(edges_y)
    top = max(edges_y)
    height = top - bottom

    left = min(edges_x)           
    right = max(edges_x)             
    height = top - bottom 
    width = right - left
    # 裁剪
    res_image = image[bottom:bottom+height, left:left+width]

    # 存到本地/tmp/target
    filename = source.split('/')[-1]
    save_path = f'/tmp/target'
    target = os.path.join(save_path, filename)

    if not os.path.exists(save_path):
        os.mkdir(save_path)

    cv2.imwrite(target, res_image)
    return target                                          

def download_img(bucket, key):
    img_path = f'/tmp/{key.split("/")[-1]}'
    print(bucket)
    print(key)
    s3.download_file(bucket, key, img_path)
    return img_path
    

def get_content_type(suffix):
    if suffix in ['jpg', 'jpeg']:
        return 'image/jpeg'
    elif suffix == 'image/png':
        return 'image/png'
    elif suffix == 'svg':
        return 'image/svg+xml'
    return ''

def upload_img(local_path, bucket, key, content_type):
    with open(local_path, 'rb') as f:
        response = s3.put_object(
            Body=f,
            Bucket=bucket,
            Key=key,
            ContentType=content_type,
        )
        return response

def lambda_handler(event, context):
    print(json.dumps(event))
    # validate request headers api-token
    req_api_token = event['headers'].get('api-token', '')
    if req_api_token != os.environ['API_TOKEN']:
        return {
            'statusCode': 403,
            'body': 'Invalid request API-TOKEN'
        }
    # extract request body
    body = json.loads(event.get('body', {}))
    if not body:
        return {
            'statusCode': 403,
            'body': 'Invalid request body'
        }
    try:
        bucket = body['bucket']
        key = body['key']
    except Exception as e:
        return {
            'statusCode': 403,
            'body': 'Invalid request body parameters'
        }
    # download image
    source = download_img(bucket, key)
    # remove border and save locally
    target = remove_the_blackborder(source)
    print(target)
    # get image type/suffix
    suffix = key.split('.')[-1]
    # get content-type by suffix
    content_type = get_content_type(suffix)
    # upload image to s3
    response = upload_img(target, bucket, key, content_type)
    # delete source and target file from /tmp
    os.remove(source)
    os.remove(target)
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        print('Uploaded image')
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': 1,
                'message': 'Image border removed'
            })
        }
    else:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': 0,
                'message': json.dumps(response)
            })
        }

if __name__ == '__main__':
    event = {
        'body': json.dumps({
            'bucket': 'ethan-bucket-1',
            'key': 'remove-img/222.jpg'
        })
    }
    lambda_handler(event, {})
