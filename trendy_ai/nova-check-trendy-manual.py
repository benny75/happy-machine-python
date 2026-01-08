#!/usr/bin/env python3
import base64
import boto3
import json

def main():
    # 2. Open the image from the passed-in path
    image_path = "/Users/benny/git/happy-machine-report/2025-06-07/usBatch/bearishTrendyEMA/SB.D.DHI.DAILY.IP.jpg"
    with open(image_path, "rb") as image_file:
        binary_data = image_file.read()
        base_64_encoded_data = base64.b64encode(binary_data)
        base64_string = base_64_encoded_data.decode("utf-8")

    # 3. Create the Bedrock client
    client = boto3.client("bedrock-runtime", region_name="us-east-1")

    MODEL_ID = "amazon.nova-lite-v1:0"

    # Define your system prompt(s).
    system_list = [{
        "text": "You are an expert technical analyst. When the user provides you with an image of chart, recognize the and see how much it matches the description I give. If you are unable to recognize the pattern, provide a neutral response."
    }]

    prompt = (
        "give me a score from 0 to 10 on whether it matches the pattern of a bullish trend with recent pull back. "
        "on the next trading day based on basic technical analysis and the following additional rules: "
        "support is defined by whether the close of a stick is resting on a EMA, ideally having a long wick below it. the price is simply above EMA is not enough "
        "10 should be given to a strong trend with a recent minor pull back to a supporting EMA, and the price is above the EMA. "
        "7 should be given to a strong trend if there is no clear recent pull back to any supporting EMA in the last 5 trading days. "
        "return me the score and the reason why you gave that score"
    )

    # Define a "user" message including both the image and a text prompt.
    message_list = [
        {
            "role": "user",
            "content": [
                {
                    "image": {
                        "format": "jpeg",
                        "source": {"bytes": base64_string},
                    }
                },
                {
                    "text": prompt
                }
            ],
        }
    ]

    # Configure the inference parameters.
    inf_params = {"max_new_tokens": 300, "top_p": 0.1, "top_k": 20, "temperature": 0.1}

    native_request = {
        "schemaVersion": "messages-v1",
        "messages": message_list,
        "system": system_list,
        "inferenceConfig": inf_params,
    }

    # Invoke the model and extract the response body.
    response = client.invoke_model(modelId=MODEL_ID, body=json.dumps(native_request))
    model_response = json.loads(response["body"].read())

    # Extract the text content that presumably contains the score
    content_text = model_response["output"]["message"]["content"][0]["text"]

    # For simplicity, just print the score (assuming the model returns a numeric only)
    print(content_text)


if __name__ == "__main__":
    main()