import torch
from pandas import DataFrame

from trendy_ai.TrendyNet import TrendyNet
from trendy_ai.constants import model_path, DATA_SIZE
from trendy_ai.data_processing import validate_data, flatten_data

model = TrendyNet(6 * DATA_SIZE)
# Load the state dict of the saved model
model.load_state_dict(torch.load(model_path()))
# Set the model in evaluation mode
model.eval()


def predict(sticks_: DataFrame):
    if sticks_.empty:
        return []
    sticks = sticks_.iloc[-DATA_SIZE:]
    validate_data(sticks)
    result = []

    for ema_key in ["ema18", "ema50", "ema200"]:
        X = torch.tensor(flatten_data(sticks, ema_key), dtype=torch.float)

        # Run the data through the model
        output = model(X)
        # TODO maybe positive only if score very different
        # The output is likely a logit tensor, you might want to pass it through softmax for probabilities
        probabilities = torch.nn.functional.softmax(output, dim=-1)
        # Get the predicted class
        _, predicted_class = torch.max(probabilities, dim=-1)

        if predicted_class:
            print(f"look nice: {probabilities}")
            result.append(ema_key)

    return result
