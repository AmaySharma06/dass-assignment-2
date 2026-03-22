import os
import time

os.chdir('/home/amay/Desktop/Codes/IIIT/Year2/Dass/Ass/zFinal_Ass/dass-assignment-2/2024101095/whitebox/')

def modify(filepath, old_text, new_text):
    with open(filepath, 'r') as f:
        content = f.read()
    if old_text not in content:
        print(f"WARN: Could not find '{old_text[:30]}' in {filepath}")
    else:
        content = content.replace(old_text, new_text)
        with open(filepath, 'w') as f:
            f.write(content)

def commit(msg):
    os.system('git add code/')
    time.sleep(2)
    os.system(f'git commit -m "{msg}"')

print("Applying 14")
modify('code/moneypoly/game.py',
       "if ui.confirm(f\"  Pay ${JAIL_FINE} fine to leave jail? (y/n): \"):\n            self.bank.collect(JAIL_FINE)\n            player.jail_info[\"in_jail\"] = False",
       "if ui.confirm(f\"  Pay ${JAIL_FINE} fine to leave jail? (y/n): \"):\n            player.deduct_money(JAIL_FINE)\n            self.bank.collect(JAIL_FINE)\n            player.jail_info[\"in_jail\"] = False")
modify('code/moneypoly/game.py',
       "player.deduct_money(JAIL_FINE)\n            self.bank.collect(JAIL_FINE)\n            player.jail_info[\"in_jail\"] = False",
       "player.deduct_money(JAIL_FINE)\n            self.bank.collect(JAIL_FINE)\n            player.jail_info[\"in_jail\"] = False")
commit("Error 14: Fix voluntary jail fine dodging")

print("Applying 15")
modify('code/moneypoly/game.py',
       "if player in self.players:\n                self.players.remove(player)\n            if self.state[\"current_index\"] >= len(self.players):",
       "if player in self.players:\n                idx = self.players.index(player)\n                self.players.remove(player)\n                if idx <= self.state[\"current_index\"]:\n                    self.state[\"current_index\"] = max(0, self.state[\"current_index\"] - 1)\n            if self.state[\"current_index\"] >= len(self.players):")
commit("Error 15: Fix array shifting skips turns")

print("Applying 16")
modify('code/moneypoly/game.py',
       "for other in self.players:\n            if other != player:\n                other.deduct_money(value)\n                player.add_money(value)",
       "for other in list(self.players):\n            if other != player:\n                other.deduct_money(value)\n                player.add_money(value)\n                self._check_bankruptcy(other)")
commit("Error 16: Fix phantom bankrupt players")

print("ALL DONE")
