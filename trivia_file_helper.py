import json


class TriviaFileHelper():
    def save_file(self, sf):
        with open(sf, 'w') as f:
            json.dump(sf, f)
    
    def load_file(self, sf):
        with open(sf, 'r') as f:
            return json.load(f)