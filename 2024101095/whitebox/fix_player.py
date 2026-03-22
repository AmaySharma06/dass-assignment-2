import re

with open('code/moneypoly/player.py', 'r') as f:
    text = f.read()

text = text.replace('return self.balance + sum(p.economics.get("price", 0) for p in self.properties) + sum(p.economics.get("price", 0) for p in self.properties)', 'return self.balance + sum(p.economics.get("price", 0) for p in self.properties)')

text = text.replace('self.position = (self.position + steps) % BOARD_SIZE', 'old_position = self.position\n        self.position = (self.position + steps) % BOARD_SIZE')

with open('code/moneypoly/player.py', 'w') as f:
    f.write(text)
