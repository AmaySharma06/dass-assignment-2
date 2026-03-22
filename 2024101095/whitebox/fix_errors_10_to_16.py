import os
import time

def read_file(path):
    with open(path, 'r') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w') as f:
        f.write(content)

def run_cmd(cmd):
    os.system(cmd)

# Error 10: Fix bank loan collateral creation
print("Error 10")
bank = read_file('code/moneypoly/bank.py')
bank = bank.replace(
'''        player.add_money(amount)
        self._loans_issued.append((player.name, amount))''',
'''        player.add_money(amount)
        self._funds -= amount
        self._loans_issued.append((player.name, amount))''')
write_file('code/moneypoly/bank.py', bank)
run_cmd('git add .')
time.sleep(2)
run_cmd('git commit -m "Error 10: Fix loan collateral creation"')

# Error 11: Fix game.py mortgage bank depletion
print("Error 11")
game = read_file('code/moneypoly/game.py')
game = game.replace(
'''        player.add_money(payout)
        self.bank.collect(-payout)''',
'''        player.add_money(payout)
        self.bank.pay_out(payout)''')
write_file('code/moneypoly/game.py', game)
run_cmd('git add .')
time.sleep(2)
run_cmd('git commit -m "Error 11: Fix mortgage bank depletion"')

# Error 12: Fix game.py birthday card poor shield
print("Error 12")
game = read_file('code/moneypoly/game.py')
game = game.replace(
'''        for other in self.players:
            if other != player and other.balance >= value:''',
'''        for other in self.players:
            if other != player:''')
write_file('code/moneypoly/game.py', game)
run_cmd('git add .')
time.sleep(3)
run_cmd('git commit -m "Error 12: Fix birthday card poor shield"')

# Error 13: Fix game.py free unmortgages
print("Error 13")
game = read_file('code/moneypoly/game.py')
game = game.replace(
'''        cost = prop.unmortgage()
        if cost == 0:
            print(f"  {prop.name} is not mortgaged.")
            return False
        if player.balance < cost:
            print(f"  {player.name} cannot afford to unmortgage {prop.name} (${cost}).")
            return False
        player.deduct_money(cost)
        self.bank.collect(cost)''',
'''        if not prop.is_mortgaged:
            print(f"  {prop.name} is not mortgaged.")
            return False
        cost = int(prop.mortgage_value * 1.1)
        if player.balance < cost:
            print(f"  {player.name} cannot afford to unmortgage {prop.name} (${cost}).")
            return False
        prop.unmortgage()
        player.deduct_money(cost)
        self.bank.collect(cost)''')
write_file('code/moneypoly/game.py', game)
run_cmd('git add .')
time.sleep(2)
run_cmd('git commit -m "Error 13: Fix free unmortgages"')

# Error 14: Fix game.py voluntary jail fine dodging
print("Error 14")
game = read_file('code/moneypoly/game.py')
game = game.replace(
'''        if ui.confirm(f"  Pay ${JAIL_FINE} fine to leave jail? (y/n): "):
            self.bank.collect(JAIL_FINE)
            player.jail_info["in_jail"] = False''',
'''        if ui.confirm(f"  Pay ${JAIL_FINE} fine to leave jail? (y/n): "):
            player.deduct_money(JAIL_FINE)
            self.bank.collect(JAIL_FINE)
            player.jail_info["in_jail"] = False''')
write_file('code/moneypoly/game.py', game)
run_cmd('git add .')
time.sleep(2)
run_cmd('git commit -m "Error 14: Fix voluntary jail fine dodging"')

# Error 15: Fix game.py array shifting skips turns
print("Error 15")
game = read_file('code/moneypoly/game.py')
game = game.replace(
'''            if player in self.players:
                self.players.remove(player)''',
'''            if player in self.players:
                idx = self.players.index(player)
                self.players.remove(player)
                if idx <= self.state["current_index"]:
                    self.state["current_index"] -= 1''')
write_file('code/moneypoly/game.py', game)
run_cmd('git add .')
time.sleep(2)
run_cmd('git commit -m "Error 15: Fix array shifting skips turns"')

# Error 16: Fix phantom bankrupt players
print("Error 16")
game = read_file('code/moneypoly/game.py')
game = game.replace(
'''    def _card_collect_from_all(self, player, value):
        for other in self.players:
            if other != player:
                other.deduct_money(value)
                player.add_money(value)''',
'''    def _card_collect_from_all(self, player, value):
        for other in list(self.players):
            if other != player:
                other.deduct_money(value)
                player.add_money(value)
                self._check_bankruptcy(other)''')
write_file('code/moneypoly/game.py', game)
run_cmd('git add .')
time.sleep(2)
run_cmd('git commit -m "Error 16: Fix phantom bankrupt players"')

