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

import json
from resources import reverse_mappings, captain_ids, character_type, stadium_map, innings_selected_map, mappings, position_map
from pyrio.stat_file_parser import HudObj 

hud = HudObj(json.load(open('decoded.hud.json')))
hudJSON = json.load(open('decoded.hud.json'))

#rosters ordered by position TODO: update to pyrio code once the positions are officially in the prod hud file.
position_rosters = []
for teamIndex, teamName in enumerate(["Away", "Home"]):
      team_position_roster = []
      for position, character in hudJSON[f"Positions {teamName}"].items():
            team_position_roster.append(reverse_mappings[character])
      position_rosters.append(team_position_roster)

#determine batting order for team currently up to bat
i = 0
team_batting_battingOrder = []
while i < 9:
      team_batting_battingOrder.append(
            reverse_mappings[
                  hud.roster(hud.batting_team())[(hud.batter_roster_location() + i) % 9]['char_id']
            ])
      i += 1

#determine batting order for team currently fielding
#currently derives this using PAs, but requested to be added to hud one day.
teamName = "Home" if (hud.fielding_team == 1) else "Away"
i = 0
max_pa = 0
max_pa_rosterLoc = 0
while i < 9:
      oStats = hud.character_offensive_stats(hud.fielding_team(), i)
      
      current_pa = oStats["At Bats"] + oStats["Walks (4 Balls)"] + oStats["Walks (Hit)"]
      
      if current_pa >= max_pa:
            max_pa = current_pa
            max_pa_rosterLoc = i
      
      i += 1

i = 0
team_fielding_battingOrder = []
while i < 9:
      # + 1 since we want batter after one with most PAs
      #Exception if fielding team hasn't batted yet, so all PAs are 0.
      if max_pa != 0:
            team_fielding_battingOrder.append(reverse_mappings[hud.roster(hud.fielding_team())[(max_pa_rosterLoc + 1 + i) % 9]['char_id']])
      else:
            
            team_fielding_battingOrder.append(reverse_mappings[hud.roster(hud.fielding_team())[i]['char_id']])
      i += 1
     
#put final gecko code together
geckoCode = ""

#GAME SETTINGS

#Set stadium - works by adjusting the cursor starting position
#TODO update to pyrio code once stadium is officially in prod hud file. 
geckoCode = geckoCode + "00750c37 " + "0000000" + hex(stadium_map[hudJSON["StadiumID"]])[2:]

# first bat - 0 = P1, 1 = P2. We are assuming  the host/P1 is the away team, so the half inning value should match who bats first.
geckoCode = geckoCode + "\n003c5f40 0000000" + hex(hud.half_inning())[2:] 

#TODO: star skill setting. Until in HUD file, assumed on.

#innings selected
#TODO update to pyrio code once innings selected is officially in prod hud file. 
geckoCode = geckoCode + "\n003c5f42 0000000" + hex(innings_selected_map[hudJSON["Innings Selected"]])[2:]

#mercy
#TODO: remove hardcoding. Until in HUD file, assumed to be on.
geckoCode = geckoCode + "\n003c5f43 00000001"

#ROSTERS

#Sets the character selected indicators on character select screen
geckoCode = geckoCode + "\n003C676E 00110001"

#make OK buttons active on character select screen
geckoCode = geckoCode + "\n00750C7F 00010001"

#put cursors on OK buttons
geckoCode = geckoCode + "\n04750c48 00000009\n04750c4C 00000009"

#make part of gecko code that puts character IDs into the roster
#putting in order of positions as that makes other parts of the code simpler.
aRosterIDs = 0x803C6726

i = 0
while i < 2:
      j = 0
      while j < 9:
            geckoCode = geckoCode + "\n00" + hex(aRosterIDs + i * 9 + j)[4:]
            nZeros = 7 if position_rosters[i][j] < 16 else 6
            geckoCode = geckoCode + " " + nZeros * "0" + hex(position_rosters[i][j])[2:]
            j += 1
      i += 1


#TODO: set superstars in batting order. Unfortunately, starring runs a function that adjusts the stats, so it's not as simple as toggling a memory address.

#TODO: set handedness. Current issue is that it sets it for a specific spot in the batting order, so it can cause issues if the batting order is changed.
#until batting order is solved, leaving out.

#set team captain
captainCharIDs = [
      reverse_mappings[hud.roster(0)[hud.captain_index(0)]['char_id']],
      reverse_mappings[hud.roster(1)[hud.captain_index(1)]['char_id']]
]

awayCaptainZeros = 7 if captainCharIDs[0] < 16 else 6
homeCaptainZeros = 7 if captainCharIDs[1] < 16 else 6

geckoCode += "\n04353080 " + awayCaptainZeros * "0" + hex(captainCharIDs[0])[2:]
geckoCode += "\n04353084 " + homeCaptainZeros * "0" + hex(captainCharIDs[1])[2:]

#team logo - TODO currently set as a default based on the captain, but should improve to be based on composition of the team.
#hopefully, this is eventually in the hud file directly, which would make this viable for league play.
awayLogoZeros = 7 if captain_ids.index(captainCharIDs[0])*4 < 16 else 6
homeLogoZeros = 7 if captain_ids.index(captainCharIDs[1])*4 < 16 else 6

geckoCode += "\n003530AD " + awayLogoZeros * "0" + hex(captain_ids.index(captainCharIDs[0])*4)[2:]
geckoCode += "\n003530AE " + homeLogoZeros * "0" + hex(captain_ids.index(captainCharIDs[1])*4)[2:]



# IN GAME VALUES

# If statement is used to make this code run until the "game started indicator" is true.
# its a 16 but write since I can't find the code for an 8 bit write, but the address before it is 0 at the start of the game
geckoCode += "\n28892ab4 00000000" #start if statement

#inning
geckoCode += "\n048928A0 0000000" + hex(hud.inning())[2:]
geckoCode += "\n0089294D 0000000" + str(hud.half_inning())

#indicators for which team is fielding and batting. Need to flip each if starting in bottom of inning.
geckoCode += "\n04892998 0000000" + str(hud.batting_team()) #team batting
geckoCode += "\n0489299C 0000000" + str(hud.fielding_team()) #team fielding

#scores - need to fill the current score and the 1st inning score memory locations, otherwise scoring a run will cause the score to be wrong.
#TODO: later version. Set prior innings scores properly when the info is available in the hud files.
#TODO: currently assumes away is always P1 and home is always P2, so will need to adjust if that is not the case.
awayScore = hud.score(0)
homeScore = hud.score(1)

homeScoreZeros = 7 if homeScore < 16 else 6
awayScoreZeros = 7 if awayScore < 16 else 6

geckoCode += "\n028928A4 " + awayScoreZeros * "0" + hex(awayScore)[2:] #current scores
geckoCode += "\n028928CA " + homeScoreZeros * "0" + hex(homeScore)[2:]

geckoCode += "\n028928A6 " + awayScoreZeros * "0" + hex(awayScore)[2:] #inning 1 scores
geckoCode += "\n028928CC " + homeScoreZeros * "0" + hex(homeScore)[2:]


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
aStamina = 0x803535d8
gapPlayer = 0x803535f6 - 0x803535d8
gapTeam = gapPlayer * 9
for team in range(2):
      if team == hud.batting_team():
            startingBattingPosition = hud.batter_roster_location()
      else:
            startingBattingPosition = (max_pa_rosterLoc + 1) % 9

      for battingPos in range(9):
            stamina = hud.character_defensive_stats(team, (startingBattingPosition + battingPos) % 9)['Stamina']
            geckoCode += "\n02" + hex(aStamina + team * gapTeam + battingPos * gapPlayer)[4:] + " 0000000" + hex(stamina)[2:]
            
#Character positions - done by setting the roster in the order of the positions, so no extra code needed.
#it involves fixing the struct at 0x808929c8
#try using the presumed batting order (so assume the player put the batting order correctly whens starting)
aBattingPositionStruct = 0x808929c8
gapCharacter = 0x8
gapTeam = gapCharacter * 10
teamNames = ["Away", "Home"] #always assumes P1 is away

for teamNum, teamName in enumerate(teamNames):

      battingOrder = team_batting_battingOrder if teamNum == hud.half_inning() else team_fielding_battingOrder

      for positionNum in range(10):

            if positionNum == 0: #first slot is the pitcher
                  pitcherName = hudJSON[f"Positions {teamName}"]["P"]
                  pitcherRosterSpot = -1
                  #TODO fix home and away to use right batting order (fielding or batting)
                  for position, characterID in enumerate(battingOrder):
                        characterName = mappings[characterID]
                        if characterName == pitcherName:
                              pitcherRosterSpot = position
                              break

                  geckoCode += "\n04" + hex(aBattingPositionStruct + teamNum * gapTeam)[4:] + " 0000000" + str(pitcherRosterSpot)
                  geckoCode += "\n04" + hex(aBattingPositionStruct + teamNum * gapTeam + 0x4)[4:] + " 00000000"

            else:
                  characterName = mappings[battingOrder[positionNum - 1]]
                  characterPosition = None
                  for position, character in hudJSON[f"Positions {teamName}"].items():
                        if character == characterName:
                              characterPosition = position_map[position]
                              break                  
                  
                  #geckoCode += "\n04" + hex(aBattingPositionStruct + teamNum * gapTeam + positionNum * gapCharacter)[4:] + " 0000000" + str(positionNum - 1) not needed since always the same order.
                  geckoCode += "\n04" + hex(aBattingPositionStruct + teamNum * gapTeam + positionNum * gapCharacter + 0x4)[4:] + " 0000000" + str(characterPosition)



#runners
#adds some nop instructions for the function calls that remove baserunners.
aNopLocation = 0x806c93f0
nopLocGap = 0x30 
aRosterID0 = 0x8088eef8
rosterIDGap = 0x154

for runnerNum in [1, 2, 3]:
      if hud.runner_on_base(runnerNum):
            runnerCharID = reverse_mappings[hud.runner(runnerNum).get("Runner Char Id", -1)]
            runnerRosterSpot = team_batting_battingOrder.index(runnerCharID)
            zerosCharID = 7 if runnerCharID < 16 else 6

            geckoCode += "\n02" + hex(aRosterID0 + rosterIDGap * runnerNum)[4:] + " 0000000" + str(runnerRosterSpot)
            geckoCode += "\n02" + hex(aRosterID0 + rosterIDGap * runnerNum + 2)[4:] + " " + zerosCharID * "0" + hex(runnerCharID)[2:]
            geckoCode += "\n04" + hex(aNopLocation + nopLocGap * runnerNum)[4:] + " 60000000"

#below code takes into account what happened on the pitch due to weirdness in the hud. Going to revert back to the previous pitch, so no need for this logic.
# for runnerNum in range(4):
#       if hud.runner_on_base(runnerNum):
#             resultBase = hud.runner(runnerNum).get("Runner Result Base", -1)
#             if resultBase in [1, 2, 3]:
#                   runnerCharID = reverse_mappings[hud.runner(runnerNum).get("Runner Char Id", -1)]
#                   runnerRosterSpot = team_batting_battingOrder.index(runnerCharID)
#                   zerosCharID = 7 if runnerCharID < 16 else 6

#                   geckoCode += "\n02" + hex(aRosterID0 + rosterIDGap * resultBase)[4:] + " 0000000" + str(runnerRosterSpot)
#                   geckoCode += "\n02" + hex(aRosterID0 + rosterIDGap * resultBase + 2)[4:] + " " + zerosCharID * "0" + hex(runnerCharID)[2:]
#                   geckoCode += "\n04" + hex(aNopLocation + nopLocGap * resultBase)[4:] + " 60000000"

#end if statement, check if the converse is true for any post-processing code
geckoCode += "\n2A892ab5 00000000" #end first if statement, check if the converse is true (<> 0)

#restore nop'd runner instructions to prevent overwriting the runners after the start of the game.
geckoCode += "\n04" + hex(aNopLocation + nopLocGap * 1)[4:] + " B0650234"
geckoCode += "\n04" + hex(aNopLocation + nopLocGap * 2)[4:] + " B06500E0"
geckoCode += "\n04" + hex(aNopLocation + nopLocGap * 3)[4:] + " B06500E0"

#TODO: very longterm adjust the player's stats so that the hud file is more accurate.     

print(geckoCode)

if hud.half_inning() == 0:
      print("Away team batting order: ", [mappings[x] for x in team_batting_battingOrder])
      print("Home team batting order: ", [mappings[x] for x in team_fielding_battingOrder])
else: 
      print("Away team batting order: ", [mappings[x] for x in team_fielding_battingOrder])
      print("Home team batting order: ", [mappings[x] for x in team_batting_battingOrder])

#TODO: prevent changing fielder locations pre-game.
#TODO: prevent moving the cursor in character select screen, stadium select, and game settings.
