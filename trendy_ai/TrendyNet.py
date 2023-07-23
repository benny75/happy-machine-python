import torch
from torch import nn, optim


# Define the model architecture
class TrendyNet(nn.Module):
    def __init__(self, input_size):
        super(TrendyNet, self).__init__()
        # Adjust the number of neurons in each layer and add/remove layers as needed
        self.fc1 = nn.Linear(input_size, 256)
        self.fc2 = nn.Linear(256, 32)
        self.fc3 = nn.Linear(32, 2)
        self.optimizer = optim.Adam(self.parameters(), lr=0.01)
        self.loss_fn = nn.CrossEntropyLoss()

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        x = self.fc3(x)
        return x

    def train_model(self, X_train, y_train):
        self.train()
        self.optimizer.zero_grad()
        output = self(X_train)
        loss = self.loss_fn(output, y_train)
        loss.backward()
        self.optimizer.step()
        return loss.item()

    def validate(self, X_val, y_val):
        self.eval()
        with torch.no_grad():
            output = self(X_val)
            loss = self.loss_fn(output, y_val)
        return loss.item()
