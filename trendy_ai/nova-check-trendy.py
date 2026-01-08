import sys
import base64
import boto3
import json
import logging

# Configure logging
logging.basicConfig(
    filename="nova-check-trendy.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def main():
    logging.info("Script started")

    if len(sys.argv) < 2:
        logging.error("No signal type provided")
        print(f"Usage: {sys.argv[0]} <bullish|bearish>", file=sys.stderr)
        sys.exit(1)

    signal_type = sys.argv[1].lower()
    if signal_type not in ["bullish", "bearish"]:
        logging.error(f"Invalid signal type: {signal_type}")
        print("Invalid signal type. Use 'bullish' or 'bearish'.", file=sys.stderr)
        sys.exit(1)

    logging.info(f"Signal type: {signal_type}")

    try:
        binary_data = sys.stdin.buffer.read()
        logging.info("Read input data from stdin")
    except Exception as e:
        logging.error(f"Error reading input data: {e}")
        sys.exit(1)

    base_64_encoded_data = base64.b64encode(binary_data)
    base64_string = base_64_encoded_data.decode("utf-8")
    logging.info("Encoded input data to Base64")

    client = boto3.client("bedrock-runtime", region_name="us-east-1")
    MODEL_ID = "amazon.nova-lite-v1:0"

    system_list = [{
        "text": "You are an expert technical analyst. When the user provides you with an image of a chart, recognize the technical pattern and provide a bullish or bearish trend prediction. If you are unable to recognize the pattern, provide a neutral response."
    }]

    if signal_type == "bullish":
        prompt = (
        "give me a score from 0 to 10 on whether it matches the pattern of a bullish trend with recent pull back. "
        "on the next trading day based on basic technical analysis and the following additional rules: "
        "support is defined by whether the close of a stick is resting on a EMA, ideally having a long wick below it. the price is simply above EMA is not enough "
        "10 should be given to a strong trend with a recent minor pull back to a supporting EMA, and the price is above the EMA. "
        "7 should be given to a strong trend if there is no clear recent pull back to any supporting EMA in the last 5 trading days. "
        "return me the score only"
        )
    else:
        prompt = (
        "give me a score from 0 to 10 on whether it matches the pattern of a bearish trend with recent pull back. "
        "on the next trading day based on basic technical analysis and the following additional rules: "
        "support is defined by whether the close of a stick is resting on a EMA, ideally having a long wick below it. the price is simply above EMA is not enough "
        "10 should be given to a strong trend with a recent minor pull back to a resisting EMA, and the price is below the EMA. "
        "7 should be given to a strong trend if there is no clear recent pull back to any resisting EMA in the last 5 trading days. "
        "return me the score only"
        )

    message_list = [
        {
            "role": "user",
            "content": [
                {"image": {"format": "jpeg", "source": {"bytes": base64_string}}},
                {"text": prompt}
            ]
        }
    ]

    inf_params = {"max_new_tokens": 300, "top_p": 0.1, "top_k": 20, "temperature": 0.3}

    native_request = {
        "schemaVersion": "messages-v1",
        "messages": message_list,
        "system": system_list,
        "inferenceConfig": inf_params,
    }

    logging.info("Sending request to Bedrock model")
    try:
        response = client.invoke_model(modelId=MODEL_ID, body=json.dumps(native_request))
        model_response = json.loads(response["body"].read())
        content_text = model_response["output"]["message"]["content"][0]["text"]
        logging.info("Received response from model")
    except Exception as e:
        logging.error(f"Error invoking model: {e}")
        sys.exit(1)

    logging.info(f"response:: {content_text}")
    logging.info("Script completed successfully")
    print(content_text)


if __name__ == "__main__":
    main()
