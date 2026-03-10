#Auto-reset gecko code generator. Allows for quick resets after crashes using the HUD file.
#Reverts back to the previous pitch before the crash.
#Made my MORI and Nuche

#assumes P1/the host is the away team.

#How to use
#Run the gecko code on the hud file from the crashed game.
#Apply the gecko code to the match.
#P1 and P2 press A until the batting order screen. Ignore the wrong graphics on the character select screens.
#Set the batting order manually, but with the next batters at the top of the lineups. Ensure superstars and handedness are correct.
#Press A through the stadium and game option select screens. Again, ignore the graphics.
#The game should start up with the exact situation prior to the crash. 

#in future versions, the goal is the make the batting order more automated, and fix the graphics. 
# List of future improvements:
# - set batting order automatically
# - set handedness
# - set superstar
# - set total hits, so they appear correct between innings
# - set stats so the book appears correct.

import json
from pyrio.stat_file_parser import HudObj, RunnerObj
from pyrio.lookup import Lookup, LookupDicts

lookup = Lookup()

hud = HudObj(json.load(open('decoded.hud.json')))

#set which player is away. 0 for P1, 1 for P2.
#TODO: test both options work
awayPlayer = 1 

#rosters ordered by position 
position_rosters = []

for teamIndex in range(2):
      team_position_roster = []
      team_roster = hud.roster(teamIndex, output_format="ID")
      for positionIndex in range(9):
            placeInOrder = hud.roster_ID_at_position(teamIndex, positionIndex)
            team_position_roster.append(team_roster.get(placeInOrder).get('char_id'))
      position_rosters.append(team_position_roster)

#determine batting orders
team_batting_battingOrder = hud.due_up(hud.batting_team(), output_format="ID")
team_fielding_battingOrder = hud.due_up(hud.fielding_team(), output_format="ID")
     
#put final gecko code together
geckoCode = ""

#add if statement if on main menu (rel = 4)
geckoCode += "280e877c 00000004" 

#GAME SETTINGS

#Set stadium - works by adjusting the cursor starting position
geckoCode += "\n00750c37 " + "0000000" + hex(lookup.lookup(LookupDicts.STADIUM, hud.stadium()))[2:]
geckoCode += "\n02650586 00000000" #prevent right cursor movement
geckoCode += "\n02650536 00000000" #prevent left cursor movement

# first bat - 0 = P1, 1 = P2. If away team is P1, then half inning matches first bat. Otherwise, invert.
if awayPlayer == 0:
      geckoCode += "\n003c5f40 0000000" + hex(hud.half_inning())[2:]
else:      
      geckoCode += "\n003c5f40 0000000" + hex(1 - hud.half_inning())[2:]

#star skill setting. 
geckoCode += "\n003c5f41 0000000" + str(hud.star_skills_setting())

#innings selected
#this address sets the menu option, so we need to translate the innings selected to the menu index
#doing the opposite of what the game actually does with bit shifting
inningsSelectedMenuIndex = (hud.inningsSelected() - 1) >> 1
geckoCode +="\n003c5f42 0000000" + str(inningsSelectedMenuIndex)

#mercy
geckoCode += "\n003c5f43 0000000" + str(hud.mercy_setting())

#prevent moving the cursor on this screen
geckoCode += "\n02049616 00000000"
geckoCode += "\n020495da 00000000"

#ROSTERS

#Sets the character selected indicators on character select screen
geckoCode += "\n003C676E 00110001"

#make OK buttons active on character select screen
geckoCode += "\n00750C7F 00010001"

#put cursors on OK buttons
geckoCode += "\n04750c48 00000009\n04750c4C 00000009"

#prevent moving the cursor on character select screen
geckoCode += "\n0464df60 60000000"

#make part of gecko code that puts character IDs into the roster
#putting in order of positions as that makes other parts of the code simpler.
aRosterIDs = 0x803C6726

for teamNum in range(2):
      for charNum in range(9):
            characterID = position_rosters[((teamNum + awayPlayer) % 2)][charNum]
            nZeros = 7 if characterID < 16 else 6

            geckoCode += "\n00" + hex(aRosterIDs + teamNum * 9 + charNum)[4:] + " " + nZeros * "0" + hex(characterID)[2:]


#set team captain
#TODO: test new output format code
captainCharIDs = [
      hud.captain(0, "ID"),
      hud.captain(1, "ID")
]

p1CaptainZeros = 7 if captainCharIDs[awayPlayer] < 16 else 6
p2CaptainZeros = 7 if captainCharIDs[1 - awayPlayer] < 16 else 6

geckoCode += "\n04353080 " + p1CaptainZeros * "0" + hex(captainCharIDs[awayPlayer])[2:]
geckoCode += "\n04353084 " + p2CaptainZeros * "0" + hex(captainCharIDs[1 - awayPlayer])[2:]

#team logo 
#TODO: test new code
p1Logo = lookup.lookup(LookupDicts.TEAM_NAME, hud.logo(awayPlayer))
p2Logo = lookup.lookup(LookupDicts.TEAM_NAME, hud.logo(1 - awayPlayer))

p1LogoZeros = 7 if p1Logo < 16 else 6
p2LogoZeros = 7 if p2Logo < 16 else 6

geckoCode += "\n003530AD " + p1LogoZeros * "0" + hex(p1Logo)[2:]
geckoCode += "\n003530AE " + p2LogoZeros * "0" + hex(p2Logo)[2:]



# IN GAME VALUES
#if statement for if the game state is in a match (rel = 5)
#ends prior if statement
geckoCode += "\n280e877d 00000005"

# If statement is used to make this code run until the "game started indicator" is true.
# its a 16 bit write since I can't find the code for an 8 bit write, but the address before it is 0 at the start of the game
geckoCode += "\n28892ab4 00000000" #start if statement

#inning
geckoCode += "\n048928A0 0000000" + hex(hud.inning())[2:]
geckoCode += "\n0089294D 0000000" + str(hud.half_inning())

#indicators for which team is fielding and batting. Need to flip each if starting in bottom of inning.
geckoCode += "\n04892998 0000000" + str(hud.batting_team()) #team batting
geckoCode += "\n0489299C 0000000" + str(hud.fielding_team()) #team fielding

#scores - need to fill the current score and the 1st inning score memory locations, otherwise scoring a run will cause the score to be wrong.
#TODO: test new pyrio code and all the inning scores are working

aScores = 0x808928a4
gapInning = 0x2
gapTeam = gapInning * 19

for team in range(2):
      inningScores = hud.inning_scores(((team + awayPlayer) % 2))

      for i in range(1 + hud.inning()):
            #first index is for the current score, rest are the per-inning scores

            if i == 0: #current score
                  score = hud.score(0)
            else: #inning scores
                  score = inningScores[i - 1]
            
            zeros = 7 if score < 16 else 6

            geckoCode += "\n02" + hex(aScores + gapTeam * team + gapInning * i)[4:] + " " + zeros * "0" + hex(score)[2:]

#count
geckoCode += "\n04892968 0000000" + str(hud.strikes())
geckoCode += "\n0489296C 0000000" + str(hud.balls())
geckoCode += "\n04892970 0000000" + str(hud.outs())
geckoCode += "\n04892974 0000000" + str(hud.outs()) #stored outs

#team stars
geckoCode += "\n00892ad6 0000000" + str(hud.team_stars(0)) #away team stars
geckoCode += "\n00892ad7 0000000" + str(hud.team_stars(1)) #home team stars

#star chance active
geckoCode += "\n00892ad8 0000000" + str(hud.star_chance())

#pitcher stamina.
#TODO: confirm works correctly when P1 is home.
aStamina = 0x803535d8
gapPlayer = 0x803535f6 - 0x803535d8
gapTeam = gapPlayer * 9
for team in range(2):
      startingBattingPosition = hud.batter_roster_location(((team + awayPlayer) % 2))

      for battingPos in range(9):
            stamina = hud.character_defensive_stats(((team + awayPlayer) % 2), (startingBattingPosition + battingPos) % 9)['Stamina']
            geckoCode += "\n02" + hex(aStamina + team * gapTeam + battingPos * gapPlayer)[4:] + " 0000000" + hex(stamina)[2:]
            
#Character positions - 
#Characters are loaded in roster by positions, so only need to set struct that holds batting order and position
#Assumes players set the batting order correctly.
#TODO: test new pyrio version
aBattingPositionStruct = 0x808929c8
gapCharacter = 0x8
gapTeam = gapCharacter * 10

for teamNum in range(2):
      for index in range(10):
      #in this struct, first index is the pitcher, and 1-9 are batting order

            if index == 0: #first slot is the pitcher
                  geckoCode += "\n04" + hex(aBattingPositionStruct + teamNum * gapTeam)[4:] + " 0000000" + str(hud.roster_ID_at_position(((teamNum + awayPlayer) % 2), "P"))
                  geckoCode += "\n04" + hex(aBattingPositionStruct + teamNum * gapTeam + 0x4)[4:] + " 00000000"

            else:
                  geckoCode += "\n04" + hex(aBattingPositionStruct + teamNum * gapTeam + index * gapCharacter + 0x4)[4:] + " 0000000" + (
                        str(lookup.lookup(LookupDicts.POSITION, hud.position(((teamNum + awayPlayer) % 2), index - 1))))



#runners
#adds some nop instructions for the function calls that remove baserunners.
#TODO: test new pyrio code, especually with the newRosterSpot
aNopLocation = 0x806c93f0
nopLocGap = 0x30 
aRosterID0 = 0x8088eef8
rosterIDGap = 0x154

for runnerNum in [1, 2, 3]:
      if hud.runner_on_base(runnerNum):
            runner = RunnerObj(hud.runner(runnerNum))

            newRosterSpot = (runner.roster_location() - hud.batter_roster_location()) % 9
            zerosCharID = 7 if runner.character("ID") < 16 else 6

            geckoCode += "\n02" + hex(aRosterID0 + rosterIDGap * runnerNum)[4:] + " 0000000" + str(newRosterSpot)
            geckoCode += "\n02" + hex(aRosterID0 + rosterIDGap * runnerNum + 2)[4:] + " " + zerosCharID * "0" + runner.character("IDHex")[2:]
            geckoCode += "\n04" + hex(aNopLocation + nopLocGap * runnerNum)[4:] + " 60000000"

#end if statement, check if the converse is true for any post-processing code
geckoCode += "\n2A892ab5 00000000" #end first if statement, check if the converse is true (<> 0)

#restore nop'd runner instructions to prevent overwriting the runners after the start of the game.
geckoCode += "\n04" + hex(aNopLocation + nopLocGap * 1)[4:] + " B0650234"
geckoCode += "\n04" + hex(aNopLocation + nopLocGap * 2)[4:] + " B06500E0"
geckoCode += "\n04" + hex(aNopLocation + nopLocGap * 3)[4:] + " B06500E0"   

print(geckoCode)
for i in range(2):
      print(f"P{i+1} batting order")

      if (awayPlayer == 0 and hud.half_inning() == 0) or (awayPlayer == 1 and hud.half_inning() == 1): 
            teamNum = i
      else:
        teamNum = 1 - i

      roster = hud.roster(teamNum, output_format="name")

      for playerNum in range(9):
            rosterLocation = (playerNum + hud.batter_roster_location(teamNum)) % 9
            print("   ", 
                  hud.characterId(teamNum, rosterLocation), 
                  hud.batting_hand(teamNum, rosterLocation)[:1], 
                  hud.fielding_hand(teamNum, rosterLocation)[:1],
                  "Superstar" if hud.isSuperstar(teamNum, rosterLocation) else "") #TODO test this
      print("") #new line
