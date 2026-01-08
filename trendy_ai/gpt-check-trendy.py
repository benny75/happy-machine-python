import sys
import base64
import json
import logging
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    filename="gpt-check-trendy.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def main():
    logging.info("Script started")

    if len(sys.argv) < 2:
        logging.error("No signal type provided")
        print(f"Usage: {sys.argv[0]} <bullish|bearish> [model_id]", file=sys.stderr)
        sys.exit(1)

    signal_type = sys.argv[1].lower()
    if signal_type not in ["bullish", "bearish"]:
        logging.error(f"Invalid signal type: {signal_type}")
        print("Invalid signal type. Use 'bullish' or 'bearish'.", file=sys.stderr)
        sys.exit(1)

    # Get model ID from args or default
    if len(sys.argv) > 2:
        model_id = sys.argv[2]
    else:
        model_id = "gpt-5.2-pro-2025-12-11"

    logging.info(f"Signal type: {signal_type}")
    logging.info(f"Model ID: {model_id}")

    try:
        binary_data = sys.stdin.buffer.read()
        logging.info("Read input data from stdin")
    except Exception as e:
        logging.error(f"Error reading input data: {e}")
        sys.exit(1)

    base_64_encoded_data = base64.b64encode(binary_data)
    base64_string = base_64_encoded_data.decode("utf-8")
    logging.info("Encoded input data to Base64")

    # Initialize OpenAI client with API key
    client = OpenAI(
        # api_key is automatically loaded from OPENAI_API_KEY env var
        api_key=os.getenv("OPENAI_API_KEY"), 
    )

    system_message = """
    You are a financial chart analysis expert specializing in trend-based trading strategies. 
    Analyze the provided chart image showing OHLC (Open, High, Low, Close) data and EMA (Exponential Moving Average) indicators.
    
    Evaluate if the chart shows a strong {} trend based on:
    1. Price action relative to EMAs - specifically look for support/resistance at EMAs
    2. EMA alignment (shorter above longer for bullish, below for bearish)
    3. Recent price momentum and volatility
    4. IMPORTANT: Look for recent pullbacks to supportive/resistive EMAs in the last 5 periods
    5. Check for long wicks below candles at EMAs (for bullish) or above (for bearish) indicating strong rejection
    
    For a bullish trend:
    - Score 100: Strong uptrend with a recent minor pullback to a supporting EMA, price closed above EMA with rejection wicks
    - Score 70: Strong uptrend without clear recent pullback to supporting EMAs in last 5 periods
    - Score 50: Neutral or unclear trend direction
    - Score 0: Strong bearish trend with no bullish indicators
    
    For a bearish trend:
    - Score 100: Strong downtrend with a recent minor pullback to a resistive EMA, price closed below EMA with rejection wicks
    - Score 70: Strong downtrend without clear recent pullback to resistive EMAs in last 5 periods
    - Score 50: Neutral or unclear trend direction
    - Score 0: Strong bullish trend with no bearish indicators
    
    Return only a single number from 0 to 100 representing the strength of the {} trend.
    Return only the number, no explanation or other text.
    """.format(signal_type, signal_type)

    user_message = """
    Based on this chart image, what is the {} trend strength score (0-100)?
    """.format(signal_type)

    logging.info("Sending request to OpenAI model using Responses API")
    try:
        response = client.responses.create(
            model=model_id,
            instructions=system_message,
            input=[
                {
                    "role": "user", 
                    "content": [
                        {
                            "type": "input_image", 
                            "image_url": f"data:image/jpeg;base64,{base64_string}",
                            "detail": "auto"
                        },
                        {
                            "type": "input_text", 
                            "text": user_message
                        }
                    ]
                }
            ],
            # temperature=0.3, # Removed as it is not supported with this model
            max_output_tokens=300,
        )
        
        # Extract content text from the response using convenience property
        content_text = response.output_text
        if not content_text:
            logging.error(f"Empty response text. Response: {response}")
            content_text = "0"
            
        logging.info("Received response from model")
    except Exception as e:
        logging.error(f"Error invoking model: {e}")
        sys.exit(1)

    logging.info(f"response:: {content_text}")
    logging.info("Script completed successfully")
    print(content_text)


if __name__ == "__main__":
    main()
