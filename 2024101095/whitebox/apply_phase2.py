import os
import time

os.chdir('/home/amay/Desktop/Codes/IIIT/Year2/Dass/Ass/zFinal_Ass/dass-assignment-2/2024101095/whitebox/')

def modify(filepath, old_text, new_text):
    with open(filepath, 'r') as f:
        content = f.read()
    if old_text not in content:
        raise Exception(f"Could not find old_text in {filepath}:\n'{old_text[:30]}'")
    content = content.replace(old_text, new_text)
    with open(filepath, 'w') as f:
        f.write(content)

def commit(msg):
    os.system('git add code/')
    time.sleep(2)
    os.system(f'git commit -m "{msg}"')

print("Applying 1")
modify('code/moneypoly/dice.py', "random.randint(1, 5)", "random.randint(1, 6)")
commit("Error 1: Fix dice range constraint")

print("Applying 2")
modify('code/moneypoly/player.py', 
       "return self.balance", 
       "return self.balance + sum(p.economics.get('price', 0) for p in self.properties)")
commit("Error 2: Fix player net worth calculation")

print("Applying 3")
modify('code/moneypoly/game.py', 
       "return min(self.players,", 
       "return max(self.players,")
commit("Error 3: Fix winner calculation")

print("Applying 4")
modify('code/moneypoly/property.py', 
       "return any(p.owner == player", 
       "return all(p.owner == player")
commit("Error 4: Fix full monopoly requirement")

print("Applying 5")
modify('code/moneypoly/game.py', 
       "if player.balance <= prop.economics[\"price\"]:", 
       "if player.balance < prop.economics[\"price\"]:")
commit("Error 5: Fix property purchase boundary")

print("Applying 6")
modify('code/moneypoly/player.py', 
       "self.position = (self.position + steps) % BOARD_SIZE\n\n        if self.position == 0:",
       "old_position = self.position\n        self.position = (self.position + steps) % BOARD_SIZE\n\n        if self.position < old_position or self.position == 0:")
commit("Error 6: Fix Go pass salary")

print("Applying 7")
modify('code/moneypoly/game.py',
       "player.deduct_money(rent)\n        print",
       "player.deduct_money(rent)\n        prop.owner.add_money(rent)\n        print")
commit("Error 7: Fix rent liquidity sink")

print("Applying 8")
modify('code/moneypoly/game.py',
       "buyer.deduct_money(cash_amount)\n            buyer.add_property(prop)",
       "buyer.deduct_money(cash_amount)\n            seller.add_money(cash_amount)\n            buyer.add_property(prop)")
commit("Error 8: Fix trade asymmetries")

print("Applying 9")
modify('code/moneypoly/bank.py',
       "        Negative amounts are silently ignored.\n        \"\"\"\n        self._funds += amount",
       "        Negative amounts are silently ignored.\n        \"\"\"\n        if amount <= 0:\n            return\n        self._funds += amount")
commit("Error 9: Fix subzero bank input")

print("Applying 10")
modify('code/moneypoly/bank.py',
       "player.add_money(amount)\n        self._loans_issued.append",
       "player.add_money(amount)\n        self._funds -= amount\n        self._loans_issued.append")
commit("Error 10: Fix loan collateral creation")

print("Applying 11")
modify('code/moneypoly/game.py',
       "player.add_money(payout)\n        self.bank.collect(-payout)",
       "player.add_money(payout)\n        self.bank.pay_out(payout)")
commit("Error 11: Fix mortgage bank depletion")

print("Applying 12")
modify('code/moneypoly/game.py',
       "for other in self.players:\n            if other != player and other.balance >= value:",
       "for other in self.players:\n            if other != player:")
commit("Error 12: Fix birthday card poor shield")

print("Applying 13")
modify('code/moneypoly/game.py',
       "cost = prop.unmortgage()\n        if cost == 0:\n            print(f\"  {prop.name} is not mortgaged.\")\n            return False\n        if player.balance < cost:\n            print(f\"  {player.name} cannot afford to unmortgage {prop.name} (${cost}).\")\n            return False\n        player.deduct_money(cost)\n        self.bank.collect(cost)",
       "if not prop.is_mortgaged:\n            print(f\"  {prop.name} is not mortgaged.\")\n            return False\n        cost = int(prop.mortgage_value * 1.1)\n        if player.balance < cost:\n            print(f\"  {player.name} cannot afford to unmortgage {prop.name} (${cost}).\")\n            return False\n        prop.unmortgage()\n        player.deduct_money(cost)\n        self.bank.collect(cost)")
commit("Error 13: Fix free unmortgages")

print("Applying 14")
modify('code/moneypoly/game.py',
       "if ui.confirm(f\"  Pay ${JAIL_FINE} fine to leave jail? (y/n): \"):\n            self.bank.collect(JAIL_FINE)\n            player.jail_info[\"in_jail\"] = False",
       "if ui.confirm(f\"  Pay ${JAIL_FINE} fine to leave jail? (y/n): \"):\n            player.deduct_money(JAIL_FINE)\n            self.bank.collect(JAIL_FINE)\n            player.jail_info[\"in_jail\"] = False")
modify('code/moneypoly/game.py',
       "player.deduct_money(JAIL_FINE)\n            self.bank.collect(JAIL_FINE)\n            player.jail_info[\"in_jail\"] = False",
       "player.deduct_money(JAIL_FINE)\n            self.bank.collect(JAIL_FINE)\n            player.jail_info[\"in_jail\"] = False") # It was there a second time on line 292 but already fine.
commit("Error 14: Fix voluntary jail fine dodging")

print("Applying 15")
modify('code/moneypoly/game.py',
       "if player in self.players:\n                self.players.remove(player)",
       "if player in self.players:\n                idx = self.players.index(player)\n                self.players.remove(player)\n                if idx <= self.state[\"current_index\"]:\n                    self.state[\"current_index\"] -= 1")
commit("Error 15: Fix array shifting skips turns")

print("Applying 16")
modify('code/moneypoly/game.py',
       "for other in self.players:\n            if other != player:\n                other.deduct_money(value)\n                player.add_money(value)",
       "for other in list(self.players):\n            if other != player:\n                other.deduct_money(value)\n                player.add_money(value)\n                self._check_bankruptcy(other)")
commit("Error 16: Fix phantom bankrupt players")

print("DONE!")
