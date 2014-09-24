#---------------------------------------------------------------------------
# Constants
#---------------------------------------------------------------------------
import re
import clr

clr.AddReference("System.Drawing")
clr.AddReference("System.Windows.Forms")

from System.Drawing import Point, Color, Font, FontStyle
from System.Windows.Forms import *

def printGUID(card, x = 0, y = 0, txt = ""):
    if card.model in scriptsDict:
        txt = " (Scripted)"
    whisper("{}~{}{}".format(card, card.model, txt))

def moveCardEvent(player, card, fromGroup, toGroup, oldIndex, index, oldX, oldY, x, y, isScriptMove, highlight = None, markers = {}):
    mute()
    if player != me:
        return
    if isScriptMove:
        return
    if fromGroup == table:
        card.moveToTable(oldX,oldY)
        card.setIndex(oldIndex)
    elif fromGroup == me.hand and toGroup == me.hand:
        return
    else:
        card.moveTo(fromGroup, oldIndex)
        notify("Overriding card movement...")

def resetVars(group, x = 0, y = 0):
    for p in getPlayers():
        remoteCall(p, 'reloadLocalVars', [p])
    

def reloadLocalVars(player):
    mute()
    if player == me:
        #### Prep initial variables
        global storedCards, storedTurnPlayer, storedPhase, storedVictory, storedOppVictory, storedMission, storedGameStats, storedQueue
        storedTurnPlayer = getGlobalVariable("turnplayer")
        if storedTurnPlayer == "None":
            storedTurnPlayer = None
        else:
            storedTurnPlayer = Player(int(storedTurnPlayer))
        storedPhase = getGlobalVariable("phase")
        storedMission = eval(getGlobalVariable("activemission"))
        storedGameStats = eval(getGlobalVariable("gameStats"))
        if storedGameStats == {}: #initialize the storedGameStats
            storedGameStats = { 'fm':[], 'sm':[] }
        storedCards = eval(getGlobalVariable("cards"))
        storedQueue = eval(getGlobalVariable("cardqueue"))
        storedVictory = int(getPlayers()[1].getGlobalVariable("victory"))
        storedOppVictory = int(me.getGlobalVariable("victory"))
        
def registerTeam(player, groups):
    mute()
    reloadLocalVars(me)
    global storedPhase, storedVictory, storedOppVictory
    if player != me:  #only execute this event if its your own deck
        return
    #### The game only works with 2 players, so anyone else loading a deck will have their cards deleted
    if storedPhase not in ["pre.1reg", "pre.2reg"]:
        whisper("cannot load deck -- there are already 2 players registered.")
        for group in [me.Deck, me.piles["Mission Pile"], me.Team]:
            for c in group:
                c.delete()
        return
    #### Verify deck contents
    if len(me.Team) != 4:
        whisper("cannot load deck -- it does not have 4 team characters.")
        for group in [me.Deck, me.piles["Mission Pile"], me.Team]:
            for c in group:
                c.delete()
        return
    if len(me.piles["Mission Pile"]) != 12:
        whisper("cannot load deck -- it does not have 12 missions.")
        for group in [me.Deck, me.piles["Mission Pile"], me.Team]:
            for c in group:
                c.delete()
        return
    #### Store victory points
    victory = 0
    storeNewCards(me.Team, {"s":"r"})
    for card in me.Team:
        card.moveToTable(0,0)
        victory += int(card.Cost)  #add the card's cost to the victory total
    me.setGlobalVariable("victory", str(victory)) #Stores your opponent's victory total
    storedVictory = int(getPlayers()[1].getGlobalVariable("victory"))
    storedOppVictory = int(me.getGlobalVariable("victory"))
    notify("{} registers their Team ({} points).".format(me, victory))
    me.Deck.shuffle()
    me.piles["Mission Pile"].shuffle()
    #### Determine who goes first
    if storedPhase == "pre.1reg":
        setGlobalVariable("phase", "pre.2reg")
    #### After the second player registers their deck, the starting player can be determined
    elif storedPhase == "pre.2reg":
        opponent = getPlayers()[1]
        if storedVictory > storedOppVictory:
            startingPlayer = me
            notify("{} will play first.".format(me))
        elif storedVictory < storedOppVictory:
            startingPlayer = opponent
            notify("{} will play first.".format(startingPlayer))
        elif storedVictory == storedOppVictory:  ##randomly determine in the event of a tie
            if rnd(1,2) == 1:
                startingPlayer = me
                notify("{} will play first, chosen randomly.".format(me))
            else:
                startingPlayer = opponent
                notify("{} will play first, chosen randomly.".format(opponent))
        if startingPlayer == me:
            setGlobalVariable("turnplayer", str(me._id))
            stopPlayer = opponent
        else:
            setGlobalVariable("turnplayer", str(startingPlayer._id))
            stopPlayer = me
        notify("{} will choose a team character to Stop.".format(stopPlayer))
        global storedQueue, storedCards
        oppTeam = [c for c in storedCards if "Team Character" in Card(c).Type and not Card(c).controller == stopPlayer]
        addToQueue([(oppTeam, "game", "stopChar", 1, stopPlayer._id, False, None)])
        cleanup()
    else:
        notify("An error has occured: phase variable should be pre.1reg or pre.2reg")
        return

def playerGlobalVarChanged(player, varName, oldValue, newValue):
    mute()
    if varName == "victory":
        if player != me:
            global storedVictory
            storedVictory = int(newValue)
            return
        else:
            global storedOppVictory
            storedOppVictory = int(newValue)
            return

def globalVarChanged(varName, oldValue, newValue):
    mute()
    #### update python global variables
    if varName == "turnplayer":
        global storedTurnPlayer
        storedTurnPlayer = Player(int(newValue))
        return
    if varName == "cards":
        global storedCards
        storedCards = eval(newValue)
        return
    if varName == "activemission":
        global storedMission
        storedMission = eval(newValue)
        return
    if varName == "gameStats":
        global storedGameStats
        storedGameStats = eval(newValue)
        return
    if varName == "cardqueue":
        global storedQueue
        storedQueue = eval(newValue)
        if len(storedQueue) > 0:
            firstQueue = storedQueue[0]
            if firstQueue[1] == "res" and firstQueue[4] == me._id:
                del storedQueue[0]
#                if firstQueue[2] == "onAssign":
#                    storedQueue = scriptResolveTriggers(Card(firstQueue[6]), "onAssign") + storedQueue
                storedQueue = scriptResolveTriggers(Card(firstQueue[6]), firstQueue[2]) + storedQueue
                setGlobalVariable("cardqueue", str(storedQueue))
                cleanup()
                return
            if turnPlayer() == me:
                notify("{}: {} {} {} targets.{}".format(
                        firstQueue[2] if firstQueue[1] == "game" else "{}".format(Card(firstQueue[0])) + "'s " + firstQueue[2] + " ability",
                            Player(firstQueue[4]).name,
                               "chooses up to" if firstQueue[5] else "must choose",
                                  firstQueue[3],
                                              " (Press TAB to skip)" if firstQueue[5] else ""
                                                        ))
        return
    #### Phase Changes
    if varName == "phase":
        global storedPhase
        storedPhase = newValue
        #### First Player Mulligan
        if newValue == "pre.1mul":
            fillHand(8)
            if myTurn():
                if confirm("Do you want to draw a new hand?"):
                    for c in me.hand:
                        c.moveTo(me.Deck)
                    rnd(1,10)
                    me.Deck.shuffle()
                    rnd(1,10)
                    fillHand(8)
                    notify("{} draws a new hand.".format(me))
                else:
                    notify("{} keeps their hand.".format(me))
                setGlobalVariable("phase", "pre.2mul")
            return
        #### Second Player Mulligan
        if newValue == "pre.2mul":
            if not myTurn():
                if confirm("Do you want to draw a new hand?"):
                    for c in me.hand:
                        c.moveTo(me.Deck)
                    rnd(1,10)
                    me.Deck.shuffle()
                    rnd(1,10)
                    fillHand(8)
                    notify("{} draws a new hand.".format(me))
                else:
                    notify("{} keeps their hand.".format(me))
                turnPlayer().setActivePlayer()
                cleanup()
                notify(" ~~ {}'s Power Phase ~~ ".format(turnPlayer()))
                setGlobalVariable("phase", "pow.main")
            return
        #### Entering Power Phase
        if newValue == "pow.main":
            global storedCards
            power = 3 + len([c for c in storedCards if cardActivity(Card(c)) == "glyph"])
            me.Power = power
            notify("{} gained {} power.".format(me, power))
            #### Check for power phase script triggers
            if myTurn():
                global storedQueue
                storedQueue = phaseTriggers("onPowerEnd", None) + storedQueue
                setGlobalVariable("cardqueue", str(storedQueue))
                cleanup()
                if len(storedQueue) == 0:
                    setGlobalVariable("phase", "mis.start")
            return
        #### Setting up a new Mission
        if newValue == "mis.start":
            if myTurn():
                notify(" ~~ {}'s Mission Phase ~~ ".format(me))
                if storedMission != None:
                    notify("ERROR: There shouldn't be an active mission!")
                    return
                mission = me.piles["Mission Pile"].top()
                mission.moveToTable(0,0)
                if mission.Culture != "":
                    skilltype = "Culture"
                elif mission.Science != "":
                    skilltype = "Science"
                elif mission.Combat != "":
                    skilltype = "Combat"
                elif mission.Ingenuity != "":
                    skilltype = "Ingenuity"
                else:
                    notify("ERROR: Mission has no skill types.")
                    return
                global storedMission
                storedMission = (mission._id, skilltype, "a")
                setGlobalVariable("activemission", str(storedMission))
                notify("{}'s current mission is {}.".format(me, mission))
                storeNewCards([mission], {"s": "am"})
                ## Check for any card-specific scripts
                global storedQueue
                storedQueue = phaseTriggers("onPlayMission", mission._id) + storedQueue
                setGlobalVariable("cardqueue", str(storedQueue))
                setGlobalVariable("priority", str((turnPlayer()._id, False)))
                setGlobalVariable("phase", "mis.main")
                cleanup()
            return
        #### Resolving the current mission
        if newValue == "mis.res":
            if myTurn():
                if storedMission == None:
                    notify("ERROR: There is no registered active mission!")
                    return
                mission = Card(storedMission[0])
                type = storedMission[1]
                status = storedMission[2]
                if mission not in table:
                    mission.moveToTable(0,0)
                cleanup()
                if mission.markers[markerTypes["skill"]] >= mission.markers[markerTypes["diff"]]:
                    missionOutcome = "success"
                else:
                    missionOutcome = "failure"
                notify("{} was a {}!".format(mission, missionOutcome))
                setGlobalVariable("activemission", str((mission._id, type, missionOutcome[0])))
                setGlobalVariable("phase", "mis.sucfail")
            return
        if newValue == "mis.sucfail":
            if myTurn():
                global storedCards, storedQueue
                if storedMission == None:
                    notify("ERROR: There is no registered active mission!")
                    return
                mission = Card(storedMission[0])
                status = "Success" if storedMission[2] == "s" else "Failure"
                heroTriggers = []
                villainTriggers = []
                ## add any success or failure triggers to the queue
                for c in storedCards:
                    card = Card(c)
                    if card in table and storedCards[c]["s"] == "a" and storedCards[c].get("r" + storedMission[2], False) == False and hasTriggers(card, "on" + status, card._id):
                        if card.controller == me:
                            heroTriggers.append(c)
                        else:
                            villainTriggers.append(c)
                if hasTriggers(mission, "on" + status, mission._id): ## Add the mission's trigger if it has one
                    heroTriggers.append(mission._id)
                newQueue = []
                if len(heroTriggers) > 0: ## attach hero triggers to queue
                    newQueue += [(heroTriggers, "game", "on" + status, len(heroTriggers), turnPlayer()._id, False, None)]
                if len(villainTriggers) > 0: ## attach villain triggers to queue
                    newQueue += [(villainTriggers, "game", "on" + status, len(villainTriggers), turnPlayer(False)._id, False, None)]
                if len(newQueue) == 0: ## skip all this junk if there's no actual triggers
                    setGlobalVariable("phase", "mis.adv")
                    return
                if len(heroTriggers) > 0:
                    notify("{} has {} triggers to resolve.".format(me, status))
                else:
                    notify("{} has {} triggers to resolve.".format(turnPlayer(False), status))
                storedQueue = newQueue + storedQueue
                setGlobalVariable("cardqueue", str(storedQueue))
                cleanup()
            return
        if newValue == "mis.adv":
            if myTurn():
                if storedMission == None:
                    notify("ERROR: There is no registered active mission!")
                    return
                #### First, stop all hero characters assigned to the mission.
                global storedCards
                triggers = []
                for c in storedCards:
                    card = Card(c)
                    if card in table and storedCards[c]["s"] == "a" and card.controller != me and card.Type == "Adversary": ## add assigned adversaries to the trigger list
                        triggers.append(c)
                    elif card in table and storedCards[c]["s"] == "a" and card.controller == me and card.Type in heroTypes: ## stops all assigned hero cards
                        storedCards[c]["s"] = "s"
                        storedCards[c]["p"] = True
                    elif card not in table:
                        notify("ERROR: {} in storedCards could not be found in table!".format(card))
                setGlobalVariable("cards", str(storedCards))
                if len(triggers) == 0:
                    ## skip all this junk
                    cleanup()
                    setGlobalVariable("phase", "mis.gly")
                    return
                notify("{} has adversaries to revive.".format(turnPlayer(False)))
                global storedQueue
                storedQueue = [(triggers, "game", "revive", len(triggers), turnPlayer(False)._id, False, None)] + storedQueue
                setGlobalVariable("cardqueue", str(storedQueue))
                cleanup()
            return
        if newValue == "mis.gly":
            #### Destroy all complications and obstacles
            if not myTurn():
                global storedCards
                heroEndTriggers = []
                villainEndTriggers = []
                triggers = []
                for c in storedCards.keys():
                    card = Card(c)
                    if card not in table:
                        notify("ERROR: {} in storedCards could not be found in table!".format(card))
                    else:
                        ##find all previously assigned characters as glyph targets
                        if "p" in storedCards[c]:
                            triggers.append(c)
                            del storedCards[c]["p"]
                        if storedCards[c]["s"] == "c" and card.controller == me and card.isFaceUp == False:
                            card.moveTo(me.Discard)
                            del storedCards[c]
                        elif storedCards[c]["s"] == "a" and card.controller == me and card.Type == "Obstacle":
                            card.moveTo(me.Discard)
                            del storedCards[c]
                        ## Check for end of mission triggers
                        if cardActivity(card) == "active" and hasTriggers(card, "onMissionEnd", card._id):
                            if card.controller == me:
                                villainEndTriggers.append(c)
                            else:
                                heroEndTriggers.append(c)
                #### Check the mission's status and skip glyph step if it was a failure
                if storedMission == None:
                    notify("ERROR: There is no registered active mission!")
                    return
                mission = storedMission[0]
                status = storedMission[2]
                #### Add end of mission triggers to the queue
                newQueue = []
                if status == "s":
                    notify("{} must choose a character to earn the glyph.".format(turnPlayer()))
                    storedGameStats["sm"] += [mission] ## Add the successful mission to the game stats
                    setGlobalVariable("gameStats", str(storedGameStats))
                    newQueue += [(triggers, "game", "glyph", 1, turnPlayer()._id, False, None)]
                else:
                    #### Mission Failure
                    storedCards[mission]["s"] = "f"
                    storedGameStats["fm"] += [mission]
                    setGlobalVariable("gameStats", str(storedGameStats))
                    setGlobalVariable("activemission", "None")
                setGlobalVariable("cards", str(storedCards))
                if len(heroEndTriggers) > 0: ## attach hero triggers to queue
                    newQueue += [(heroEndTriggers, "game", "onMissionEnd", len(heroEndTriggers), turnPlayer()._id, False, None)]
                if len(villainEndTriggers) > 0: ## attach villain triggers to queue
                    newQueue += [(villainEndTriggers, "game", "onMissionEnd", len(villainEndTriggers), turnPlayer(False)._id, False, None)]
                #### if the mission was successful we need to add the glyph-granting card queue
                if len(newQueue) > 0:
                    global storedQueue
                    setGlobalVariable("cardqueue", str(newQueue + storedQueue))
                    cleanup()
                    return
                cleanup()
                setGlobalVariable("phase", "mis.end")
            return
        if newValue == "mis.end":
            if myTurn():
                global storedCards, storedGameStats
                failCount = len(storedGameStats["fm"]) ##count the number of failed missions so far
                if storedGameStats.get("nnm", [False])[0]:
                    nextMission = False ##don't continue to another mission
                    del storedGameStats["nnm"]
                    setGlobalVariable("gameStats", str(storedGameStats))
                elif me.Power < failCount:
                    nextMission = False ##don't continue to another mission
                else:
                    nextMission = confirm("Would you like to continue to another mission?\n\n({} failed missions this turn.)".format(failCount))
                for c in storedCards.keys():
                    if "m" in storedCards[c]: ## Remove skill boosts lasting until end of mission
                        del storedCards[c]["m"]
                    if "b" in storedCards[c]: ## Remove blocked status from all cards
                        del storedCards[c]["b"]
                    if "rf" in storedCards[c]: ## Remove the tag that blocks failure text
                        del storedCards[c]["rf"]
                if nextMission: ## continue to next mission
                    me.Power -= failCount
                    turnPlayer(False).Power += failCount
                    setGlobalVariable("cards", str(storedCards))
                    setGlobalVariable("phase", "mis.start")
                else: ## Skip to Debrief Phase
                    notify(" ~~ {}'s Debrief Phase ~~ ".format(me))
                    if len(addToQueue(phaseTriggers("onDebrief", None))) == 0:
                        setGlobalVariable("phase", "deb.start")
                    cleanup()
            return
        if newValue == "deb.start":
            if myTurn():
                ## Clear the successful and failed missions
                global storedGameStats
                failedMissions = storedGameStats["fm"]
                for mission in failedMissions:
                    if Card(mission) not in table:
                        failedMissions.remove(mission)
                storedGameStats["fm"] = []
                storedGameStats["sm"] = []
                ## Ready all stopped characters
                for c in storedCards.keys():
                    if storedCards[c]["s"] == "s":
                        storedCards[c]["s"] = "r"
                    if "t" in storedCards[c]: ## Remove skill boosts lasting until end of turn
                        del storedCards[c]["t"]
                setGlobalVariable("cards", str(storedCards))
                setGlobalVariable("gameStats", str(storedGameStats))
                if len(failedMissions) > 0:
                    addToQueue([(failedMissions, "game", "failMiss", len(failedMissions), turnPlayer()._id, False, None)])
                    notify("{} has failed missions to return to their mission pile.".format(me))
                else:
                    setGlobalVariable("phase", "deb.ref1")
                cleanup()
            return
        if newValue == "deb.ref1":
            if myTurn():
                handSize = len(me.hand)
                if handSize > 8:
                    notify("{} must discard {} cards, down to 8.".format(me, handSize - 8))
                    addToQueue([([], "game", "ref", handSize - 8, me._id, False, None)])
                else:
                    count = fillHand(8)
                    notify("{} refilled hand to 8, drawing {} cards.".format(me, count))
                    setGlobalVariable("phase", "deb.ref2")
            return
        if newValue == "deb.ref2":
            if not myTurn():
                handSize = len(me.hand)
                if handSize > 8:
                    notify("{} must discard {} cards, down to 8.".format(me, handSize - 8))
                    addToQueue([([], "game", "ref", handSize - 8, me._id, False, None)])
                else:
                    count = fillHand(8)
                    notify("{} refilled hand to 8, drawing {} cards.".format(me, count))
                    setGlobalVariable("phase", "deb.end")
            return
        if newValue == "deb.end":
            if myTurn():
                notify("{}'s turn ends.".format(me))
                nextPlayer = turnPlayer(False)
                nextPlayer.setActivePlayer()
                setGlobalVariable("turnplayer", str(nextPlayer._id))
                cleanup()
                notify(" ~~ {}'s Power Phase ~~ ".format(nextPlayer))
                setGlobalVariable("phase", "pow.main")

def doubleClick(card, mouseButton, keysDown):
    mute()
    ##TODO: Allow discard queue triggers to target cards in your hand (currently only works for table)
    global storedPhase, storedQueue, storedCards
    phase = storedPhase
    #### Card Queue Actions
    if storedQueue != []:
        (qCard, qTrigger, qType, qCount, qPriority, qSkippable, qSource) = storedQueue[0]
        qTargets = queueTargets()
        if Player(qPriority) != me: #### Skip if you don't have priority during the current card queue
            return
        #### Deal with game engine triggers
        if qTrigger == "game":
            #### Discarding to max hand size at debrief
            if qType == "ref":
                if card in me.hand and storedPhase in ["deb.ref1", "deb.ref2"]:
                    card.moveTo(card.owner.Discard)
                    notify("{} discards {}.".format(me, card))
                    if len(me.hand) <= 8:
                        del storedQueue[0]
                        setGlobalVariable("cardqueue", str(storedQueue))
                        if storedPhase == "deb.ref1":
                            setGlobalVariable("phase", "deb.ref2")
                        elif storedPhase == "deb.ref2":
                            setGlobalVariable("phase", "deb.end")
                return
            if card not in table:
                return
            if card._id not in qTargets:
                return #### Ignore cards that aren't in the target queue
            if card._id not in storedCards:
                notify("ERROR: {} doesn't exist in storedCards!".format(card))
                return
            if cardActivity(card) == "inactive":
                return
            #### Villain player must stop a character at the start of the game
            if qType == "stopChar":
                if phase == "pre.2reg" and not card.controller == me and not myTurn():
                    storedCards[card._id]["s"] = "s"
                    setGlobalVariable("cards", str(storedCards))
                    notify("{} stops {}.".format(me, card))
                    del storedQueue[0]
                    setGlobalVariable("cardqueue", str(storedQueue))  ## Clears the card queue
                    setGlobalVariable("phase", "pre.1mul")
                return
            #### End of Power Phase Triggers
            if qType == "onPowerEnd":
                if phase == "pow.main" and card.controller == me:
                    qTargets.remove(card._id)
                    qCount -= 1
                    if qCount == 0 or len(qTargets) == 0:
                        del storedQueue[0]
                    else:
                        storedQueue[0] = (qTargets, qTrigger, qType, qCount, qPriority, qSkippable, qSource)
                    storedQueue = triggerScripts(card, qType, None) + storedQueue
                    setGlobalVariable("cardqueue", str(storedQueue))
                    cleanup()
                    if len(storedQueue) == 0: #### no more triggers to resolve, it's safe to proceed to the next phase
                        setGlobalVariable("phase", "mis.start")
                return
            #### End of Mission Phase Triggers
            if qType == "onMissionEnd":
                if phase == "mis.gly" and card.controller == me:
                    qTargets.remove(card._id)
                    qCount -= 1
                    if qCount == 0 or len(qTargets) == 0:
                        del storedQueue[0]
                    else:
                        storedQueue[0] = (qTarget, qTrigger, qType, qCount, qPriority, qSkippable, qSource)
                    storedQueue = triggerScripts(card, qType, None) + storedQueue
                    setGlobalVariable("cardqueue", str(storedQueue))
                    cleanup()
                    if len(storedQueue) == 0: #### no more triggers to resolve, it's safe to proceed to the next phase
                        setGlobalVariable("phase", "mis.end")
                return
            #### Start of Debrief Phase Triggers
            if qType == "onDebrief":
                if phase == "mis.end" and card.controller == me:
                    qTargets.remove(card._id)
                    qCount -= 1
                    if qCount == 0 or len(qTargets) == 0:
                        del storedQueue[0]
                    else:
                        storedQueue[0] = (qTarget, qTrigger, qType, qCount, qPriority, qSkippable, qSource)
                    storedQueue = triggerScripts(card, qType, None) + storedQueue
                    setGlobalVariable("cardqueue", str(storedQueue))
                    cleanup()
                    if len(storedQueue) == 0: #### no more triggers to resolve, it's safe to proceed to the next phase
                        setGlobalVariable("phase", "deb.start")
                return
            #### Scoring/Reviving Adversaries
            if qType == "revive":
                if phase == "mis.adv" and card.controller == me and not myTurn():
                    #### Get status of mission to choose the correct action for the adversary
                    if storedMission == None:
                        notify("ERROR: There is no registered active mission!")
                        return
                    status = storedMission[2]
                    global storedGameStats
                    choiceMap = {1:"Score", 2:"Revive", 3:"Destroy"}
                    if len(me.Deck) < int(card.Revive) or storedGameStats.get("nr", [False])[0]: ## Remove the Revive option if you can't pay revive cost or if revive is disabled
                        choiceMap[2] = "Destroy"
                        del choiceMap[3]
                    if status == "s": ##Remove the Score option if the mission was a success
                        choiceMap[1] = choiceMap[2]
                        if choiceMap[2] == "Revive":
                            choiceMap[2] == choiceMap[3]
                            del choiceMap[3]
                        else:
                            del choiceMap[2]
                    elif status != "f":  ## Covers cases where the activeMission var is messed up
                        return
                    choiceList = sorted(choiceMap.values(), key=lambda x:x[1])
                    choiceResult = askChoice("Choose an action for {}".format(card.name), choiceList, [])
                    if choiceResult == 0:
                        return
                    else:
                        choiceResult = choiceMap[choiceResult]
                    #### Apply the action to the adversary
                    if choiceResult == "Score": ## Score
                        del storedCards[card._id]
                        card.moveTo(card.owner.piles["Villain Score Pile"])
                        scriptTrigger = "onScore"
                    elif choiceResult == "Revive": ## Revive
                        for c in me.Deck.top(int(card.Revive)): ## discard cards from top of deck to pay revive cost
                            c.moveTo(me.Discard)
                        storedCards[card._id]["s"] = "s" ## stops the adversary
                        scriptTrigger = "onRevive"
                    else: ## destroy
                        del storedCards[card._id]
                        card.moveTo(card.owner.Discard)
                        scriptTrigger = "onDestroy"
                    qTargets.remove(card._id)
                    qCount -= 1
                    if storedGameStats.get("nr", [False])[0]:
                        del storedGameStats["nr"]
                        setGlobalVariable("gameStats", str(storedGameStats))
                    setGlobalVariable("cards", str(storedCards))
                    if qCount == 0 or len(qTargets) == 0:
                        del storedQueue[0]
                    else:
                        storedQueue[0] = (qTargets, qTrigger, qType, qCount, qPriority, qSkippable, qSource)
                    storedQueue = triggerScripts(card, scriptTrigger, None) + storedQueue
                    setGlobalVariable("cardqueue", str(storedQueue))
                    cleanup()
                    if len(storedQueue) == 0: ## no more triggers to resolve, it's safe to proceed to the next phase
                        setGlobalVariable("phase", "mis.gly")
                return
            #### Success/Failure ability triggers
            if qType in ["onSuccess", "onFailure"]:
                if phase == "mis.sucfail" and card.controller == me:
                    qTargets.remove(card._id)
                    qCount -= 1
                    if qCount == 0 or len(qTargets) == 0:
                        del storedQueue[0]
                    else:
                        storedQueue[0] = (qTargets, qTrigger, qType, qCount, qPriority, qSkippable, qSource)
                    storedQueue = triggerScripts(card, qType, None) + storedQueue
                    setGlobalVariable("cardqueue", str(storedQueue))
                    cleanup()
                    if len(eval(getGlobalVariable("cardqueue"))) == 0: #### no more triggers to resolve, it's safe to proceed to the next phase
                        setGlobalVariable("phase", "mis.adv")
                return
            #### Earning Glyphs
            if qType == "glyph":
                if phase == "mis.gly" and card.controller == me and card.Type in ["Team Character", "Support Character"] and myTurn():
                    if storedMission == None:
                        notify("ERROR: There is no registered active mission!")
                        return
                    mission = storedMission[0]
                    glyphList = storedCards[card._id].get("g", [])
                    storedCards[card._id]["g"] = glyphList + [mission]  ## Add the glyph to the chosen character
                    storedCards[mission]["s"] = "g"  ## Sets the mission's status as an earned glyph
                    notify("{} earns the glyph ({}.)".format(card, Card(mission)))
                    del storedQueue[0]
                    setGlobalVariable("cards", str(storedCards))  ## Updates storedCards
                    setGlobalVariable("cardqueue", str(storedQueue))  ## Clears the card queue
                    setGlobalVariable("activemission", "None")  ## Empties the active mission
                    cleanup()
                    if len(storedQueue) == 0:
                        setGlobalVariable("phase", "mis.end")
                return
            #### Put failed missions to the bottom of pile
            if qType == "failMiss":
                if phase == "deb.start" and myTurn():
                    qTargets.remove(card._id)
                    qCount -= 1
                    del storedCards[card._id]
                    notify("{} puts {} on the bottom of their Mission Pile.".format(me, card))
                    card.moveToBottom(me.piles["Mission Pile"])
                    if qCount == 0 or len(qTargets) == 0:
                        del storedQueue[0]
                        setGlobalVariable("cardqueue", str(storedQueue))
                        setGlobalVariable("cards", str(storedCards))
                        cleanup()
                        setGlobalVariable("phase", "deb.ref1")
                    else:
                        storedQueue[0] = (qTargets, qTrigger, qType, qCount, qPriority, qSkippable, qSource)
                        setGlobalVariable("cardqueue", str(storedQueue))
                        setGlobalVariable("cards", str(storedCards))
                        cleanup()
                return
            #### All other GENERIC triggers
            if card.controller == me:
                qTargets.remove(card._id)
                qCount -= 1
                if qCount == 0 or len(qTargets) == 0:
                    del storedQueue[0]
                else:
                    storedQueue[0] = (qTarget, qTrigger, qType, qCount, qPriority, qSkippable, qSource)
                storedQueue = triggerScripts(card, qType, qSource) + storedQueue
                setGlobalVariable("cardqueue", str(storedQueue))
                cleanup()
            return

        #### Card Scripting Functions
        else:
            scriptCard = Card(qCard)._id
            qAction, scripts = scriptsDict[Card(scriptCard).model][qType][int(qTrigger)]
            if qAction in ["discard"]:
                if card not in me.hand:
                    return ## Discard actions can only select cards in your hand
            else:
                if cardActivity(card) == "inactive" or card._id not in qTargets:
                    return #### Ignore inactive cards and cards that aren't in the target queue
            if qAction == "statusChange":
                action = scripts["action"]
                if action == "store":
                    if "st" in storedCards[scriptCard]:
                        storedCards[scriptCard]["st"] += [card._id]
                    else:
                        storedCards[scriptCard]["st"] = [card._id]
                elif action == "stop":
                    storedCards[card._id]["s"] = "s"
                    notify("{} stops {}'s {}.".format(Card(scriptCard), me, card))
                elif action == "block":
                    blockedCards = storedCards[card._id].get("b", [])
                    if scripts.get("ignoreBlockAssign", False): ## Certain cards, like events, won't unblock when they leave play
                        storedCards[card._id]["b"] = blockedCards + [None]
                    else:
                        storedCards[card._id]["b"] = blockedCards + [scriptCard]
                    notify("{} blocks {}'s {}.".format(Card(scriptCard), me, card))
                elif action == "ready":
                    storedCards[card._id]["s"] = "r"
                    if "b" in storedCards[card._id]:
                        del storedCards[card._id]["b"]
                    notify("{} readies {}'s {}.".format(Card(scriptCard), me, card))
                elif action == "assign":
                    storedCards[card._id]["s"] = "a"
                    notify("{} assigns {}'s {}.".format(Card(scriptCard), me, card))
                elif action == "incapacitate":
                    storedCards[card._id]["s"] = "i"
                    notify("{} incapacitates {}'s {}.".format(Card(scriptCard), me, card))
                elif action == "destroy":
                    card.setController(card.owner)
                    del storedCards[card._id]
                    remoteCall(card.owner, "remoteMove", [card, 'Discard'])
                    notify("{} destroys {}'s {}.".format(Card(scriptCard), me, card))
                elif action == "mission":
                    card.setController(card.owner)
                    del storedCards[card._id]
                    remoteCall(card.owner, "remoteMove", [card, 'Mission Pile'])
                    notify("{} puts {}'s {} on top of their Mission Pile.".format(Card(scriptCard), me, card))
                else:
                    whisper("ERROR: action {} not found!".format(action))
                    return
            elif qAction == "skillChange":
                skillValue = eval(scripts["value"])
                duration = scripts["duration"]
                if scripts.get("ignoreSource", False): ## if the skill boost's source needs to be stored
                    source = None
                else:
                    source = scriptCard
                skillBoosts = storedCards[card._id].get(duration, [])
                for skillType in scripts["skill"]:
                    skillBoosts += [(skillDict[skillType], skillValue, source)]
                storedCards[card._id][duration] = skillBoosts
            elif qAction == "tagSet":
                if scripts.get("ignoreSource", False):
                    source = None
                else:
                    source = scriptCard
                duration = scripts.get("duration", "p")
                tag = scripts["tag"]
                value = scripts["value"]
                storedCards[card._id][tag] = (value, source, duration)
            elif qAction == "discard":
                card.moveTo(card.owner.Discard)
            else:
                whisper("ERROR: qAction {} not found.".format(qAction))
            #### Adjust the target count on current queue, or remove it if the last target was chosen
            if qCount > 1:
                if card._id in qTargets:
                    qTargets.remove(card._id)
                storedQueue[0] = (qCard, qTrigger, qType, qCount - 1, qPriority, qSkippable, qSource)
            else:
                del storedQueue[0]
            setGlobalVariable("cardqueue", str(storedQueue))
            setGlobalVariable("cards", str(storedCards))
            cleanup()
            ## When the queue finally empties, some specific phases need to be passed which were paused previously
            if len(storedQueue) == 0:  ## only trigger when the queue is empty
                queueSwitchPhases()
        return
    #### Phase-specific Doubleclick Actions
    if card not in table:
        return
    if cardActivity(card) == "inactive":
        whisper("You cannot perform on an inactive card.")
        return
    if not myPriority():  ## You need priority to use doubleClick
        whisper("Cannot perform action on {}: You don't have priority.".format(card))
        return
    #### general assigning character to the mission
    if phase == "mis.main":
        if card.Type not in ["Adversary", "Team Character", "Support Character"]:
            whisper("Cannot assign {}: It is not an assignable card type.".format(card))
            return
        if storedMission == None:
            whisper("Cannot assign {} as there is no active mission.".format(card))
            return
        mission = storedMission[0]
        type = storedMission[1]
        status = storedMission[2]
        cardSkill = getStats(card)[type] ## grab the card's skill value of the active mission
        if cardSkill == None:
            whisper("Cannot assign {}: Does not match the active mission's {} skill.".format(card, type))
            return
        if card._id not in storedCards:
            notify("ERROR: {} not in cards global dictionary.".format(card))
            return
        if storedCards[card._id]["s"] != "r":
            whisper("Cannot assign: {} is not Ready.".format(card))
            return
        #### check if the card is being blocked
        blockedList = storedCards[card._id].get("b", [])
        for blocker in blockedList:
            if blocker != None and blocker not in storedCards: ## If the blocker isn't in play anymore, remove it from the list.
                blockedList.remove(blocker)
        if len(blockedList) > 0:
            whisper("Cannot assign: {} is being blocked{}.".format(card, "" if blockedList == [None] else " by " + ", ".join([Card(x).name for x in blockedList if x != None])))
            return
        #### Check for additional costs that must be paid to assign the card
        addToQueue(scriptCostTriggers(card, "onAssign", card._id))
        cleanup()
        return
        
def scriptCostTriggers(card, trigger, sourceId):
    mute()
    if checkCosts(card, trigger + "Cost", sourceId) == False:
        return []
    costQueue = phaseTriggers(trigger + "Cost", sourceId) ##Put all triggered cards into the queue
    if len(costQueue) > 0: ## if there are cards with the cost trigger
        return costQueue + [([card._id], "res", trigger, 1, me._id, False, sourceId)]
    else:
        ## Finish resolving the card effect
        return scriptResolveTriggers(card, trigger)

def scriptResolveTriggers(card, trigger):
    mute()
    global storedCards
    if trigger == "onAssign":
        #### deal with blocked status
        blockedList = storedCards[card._id].get("b", [])
        for blocker in blockedList:
            if blocker != None and blocker not in storedCards: ## If the blocker isn't in play anymore, remove it from the list.
                blockedList.remove(blocker)
        if len(blockedList) == 0: ## Remove the blocked status from the card if no cards are blocking anymore
            if "b" in storedCards[card._id]:
                del storedCards[card._id]["b"]
        else:
            storedCards[card._id]["b"] = blockedList
        storedCards[card._id]["s"] = "a"  ## set status to assigned
        setGlobalVariable("cards", str(storedCards))
        notify("{} assigns {}.".format(me, card))
    elif trigger == "onPlay":
        #### Move the card to the correct location after playing it
        if card.Type == "Event":
            card.moveTo(card.owner.Discard)
        elif card.Type == "Obstacle":
            storeNewCards([card], {"s": "a"}) #assigned
            card.moveToTable(0,0)
        else:
            storeNewCards([card], {"s": "r"}) #ready
            card.moveToTable(0,0)
        notify("{} plays {}.".format(me, card))
    setGlobalVariable("priority", str((getPlayers()[1]._id, False)))
    return phaseTriggers(trigger, card._id)

def playcard(card, x = 0, y = 0):
    mute()
    global storedPhase
    if storedPhase != "mis.main":
        return
    if not myPriority():
        whisper("Cannot choose {}: You don't have priority.".format(card))
        return
    global storedQueue
    if len(storedQueue) > 0:
        whisper("Cannot play {}: There are effects that need resolving.".format(card))
        return
    if cardActivity(card) == "inactive":
        whisper("You cannot play {} during your {}turn.".format(card, "" if myTurn() else "opponent's "))
        return
    if card.Type == "Obstacle":
        if storedMission == None:
            whisper("Cannot play {} as there is no active mission.".format(card))
            return
        missionSkill = storedMission[1]
        if card.properties[missionSkill] == None or card.properties[missionSkill] == "":
            whisper("Cannot play {}: Does not match the active mission's {} skill.".format(card, missionSkill))
            return
    global storedCards
    #### Deal with Boosting cards, or preventing duplicate card names
    if card.Type in ["Team Character", "Support Character", "Adversary"]:
        matchingCards = [c for c in storedCards if Card(c).controller == me and Card(c).name == card.name and cardActivity(Card(c)) == "active"]
        for c in matchingCards: ## check the status of the matched cards
            if storedCards[c]["s"] == "a":
                ## Boost card
                if confirm("Cannot play {}: You already have a character with that name in play.\n\nBoost it?".format(card.name)):
                    card.moveTo(card.owner.Discard)
                    missionBoosts = storedCards[c].get("m", [])
                    storedCards[c]["m"] = missionBoosts + [(5, 1, 'boost')]
                    setGlobalVariable("cards", str(storedCards))
                    cleanup()
                    setGlobalVariable("priority", str((getPlayers()[1]._id, False)))
                return
            whisper("Cannot play {}: You already have a character with that name in play.".format(card))
            return
    #### Check for additional costs to play the card
#    if not checkCosts(card, "onPlayCost", card._id):
#        return
    #### Pay power cost to play card
    cardCost = int(card.Cost)
    cardScripts = scriptsDict.get(card.model, [])
    if "onGetPlayCost" in cardScripts:
        for (actionType, params) in cardScripts["onGetPlayCost"]:
            if actionType == "costChange":
                test = checkConditions(card, params.get("condition", {}), card._id)
                if checkConditions(card, params.get("condition", {}), card._id)[0] == True:
                    cardCost += eval(params["value"])
    if me.Power < cardCost:
        whisper("You do not have enough Power to play that.")
        return
    #### Check for additional costs that must be paid to assign the card
    addToQueue(scriptCostTriggers(card, "onPlay", card._id))
    me.Power -= cardCost
    cleanup()
    return

def activateAbility(card, x = 0, y = 0):
    mute()
    if not myPriority():
        whisper("Cannot activate {}'s ability: You don't have priority.".format(card))
        return
    global storedPhase
    if storedPhase != "mis.main":
        whisper("Cannot activate {}'s ability at this time.".format(card))
        return
    if cardActivity(card) == "inactive":
        whisper("You cannot activate {} during your {}turn.".format(card, "" if myTurn() else "opponent's "))
        return
    global storedQueue
    if len(storedQueue) > 0:
        whisper("Cannot activate {}: There are effect that need resolving.".format(card))
        return
    #### check for scripted abilities
    abilityText = [x for x in card.text.split('\r') if u'\u2013' in x] ## grab all abilities from card text
    if len(abilityText) == 0: ## cancel out if the card has no abilities
        return
    elif len(abilityText) == 1:
        abilityTrigger = "onAbility1"
    else:
        abilityTrigger = "onAbility" + str(askChoice("Choose an ability:", abilityText, []))
    
    #### Check for additional costs that must be paid to assign the card
    addToQueue(scriptCostTriggers(card, abilityTrigger, card._id))
    cleanup()

def checkCosts(card, type, sourceId):  ## This function verifies if all costs can be met, but doesn't actually apply the costs
    if type not in scriptsDict.get(card.model, []):
        return True
    for (actionType, params) in scriptsDict[card.model][type]:
        conditionCheck = checkConditions(card, params.get("condition", {}), None)
        if conditionCheck[0] == False:
            whisper("Cannot continue: {} does not have the required {}.".format(card, conditionCheck[1]))
            return False
        if actionType == "powerChange":
            if params["player"] == "hero":
                player = turnPlayer()
            else:
                player = turnPlayer(False)
            if player.Power + eval(params["value"]) < 0:
                whisper("Cannot continue: {} cannot pay the Power cost.".format(player))
                return False
            continue
        if actionType == "statusChange":
            targets = queueTargets(card._id, params, sourceId)
            if len(targets) == 0:
                whisper("Cannot continue: there are no valid targets for {}.".format(card))
                return False
            continue
        if actionType == "discard":
            if params["player"] == "hero":
                player = turnPlayer()
            else:
                player = turnPlayer(False)
            if len(player.hand) < eval(params["count"]):
                whisper("Cannot continue: {} does not have enough cards in their hand.".format(player))
                return False
    return True

def queueSwitchPhases():
    mute()
    global storedQueue
    if storedPhase == "mis.sucfail":
        setGlobalVariable("phase", "mis.adv")
    elif storedPhase == "mis.adv": ## shift from revive adversaries to assign glyphs
        setGlobalVariable("phase", "mis.gly")
    elif storedPhase == "mis.gly": ## move to end of mission cleanup
        setGlobalVariable("phase", "mis.end")
    elif storedPhase == "mis.end": ## move to debrief (for onDebrief triggers)
        setGlobalVariable("phase", "deb.start")

def myPriority():
    if Player(eval(getGlobalVariable("priority"))[0]) == me:
        return True
    else:
        return False

def isActive(card):
    if myTurn():
        if card.isFaceUp == False:
            if card.controller == me:
                return False
            else:
                return True
        if card.Type in heroTypes or card.Type == "Mission":
            if card.controller == me:
                return True
            else:
                return False
        else:
            if card.controller == me:
                return False
            else:
                return True
    else:
        if card.isFaceUp == False:
            if card.controller == me:
                return True
            else:
                return False
        if card.Type in heroTypes or card.Type == "Mission":
            if card.controller == me:
                return False
            else:
                return True
        else:
            if card.controller == me:
                return True
            else:
                return False

def cardActivity(card):
    mute()
    storedCards = eval(getGlobalVariable("cards"))
    status = storedCards.get(card._id, {}).get("s", "active")
    if status == "am":
        ret = "active mission"
    elif status == "c":
        ret = "complication"
    elif status == "g":
        ret = "glyph"
    elif status == "f":
        ret = "failed mission"
    else:
        ret = "active"
    if myTurn() == ((card.controller == me) == (card.Type in heroTypes) == (card.isFaceUp)):
        return ret
    else:
        return "inactive"

def turnPlayer(var = True):
    global storedTurnPlayer
    if storedTurnPlayer == None:
        hero = Player(int(getGlobalVariable("turnplayer")))
    else:
        hero = storedTurnPlayer
    if var == False:
        for p in getPlayers():
            if p != hero:
                return p
    else:
        return hero

def myTurn():
    if turnPlayer() == me:
        return True
    else:
        return False

def fillHand(maxHand):
    mute()
    count = 0
    while len(me.hand) < maxHand:
        if len(me.Deck) == 0: break
        me.Deck[0].moveTo(me.hand)
        count += 1
    return count

def storeNewCards(cards, initialState):
    mute()
    global storedCards
    for card in cards:
        cardData = dict(initialState)
        if len(storedCards) == 0:
            cardData["#"] = 1
        else:
            cardData["#"] = max([c.get("#", 0) for c in storedCards.values()]) + 1
#        for (k,v) in scriptsDict.get(card.model, {}).items():
#            for (actionType, params) in v:
#                if k == "onGetStats" and params.get("target", "self") != "self":
#                    cardData["gs"] = (True, None, "p")
        storedCards[card._id] = cardData
    setGlobalVariable("cards", str(storedCards))

def hasGlyph(glyphList, requiredGlyphs):
    mute()
    attachedGlyphs = [Card(c).Glyph for c in glyphList]
    orGlyphCheck = False
    for orGlyphs in requiredGlyphs: ## First layer of list uses OR matching
        andGlyphCheck = True
        for andGlyphs in orGlyphs: ## Second layer of list uses AND matching
            if andGlyphs not in attachedGlyphs:
                andGlyphCheck = False
        if andGlyphCheck == True and orGlyphCheck == False:
            orGlyphCheck = True
    if orGlyphCheck == False: ## Will be False if the glyph requirements aren't met
        return False
    return True

def getStats(card):
    mute()
    global storedCards
    baseSkills = {"Culture": None, "Science": None, "Combat": None, "Ingenuity": None}
    allSkillsValue = 0
    ## Set the base skill from the printed card
    for baseSkill in baseSkills.keys():
        if card.properties[baseSkill] != "":
            baseSkills[baseSkill] = int(card.properties[baseSkill])
    cardScripts = []
#    ## Scan the 
#    for (actionType, params) in scriptsDict.get(card.model, {}).get("onGetStats", []):
#        if actionType == "skillChange":
#            if params.get("target", "self") == "self":
#                cardScripts += [params]
    ## Scan all cards for global skill triggers
    for c in storedCards:
        if cardActivity(Card(c)) in ["active", "active mission"]:
            for (actionType, params) in scriptsDict.get(Card(c).model, {}).get("onGetStats", {}):
                if actionType == "skillChange":
                    targets = queueTargets(c, params, card._id)
                    if card._id in targets and checkConditions(Card(c), params.get("condition", {}), card._id)[0]:
                        cardScripts += [params]
    ## Apply static skill changes from card abilities
    for skillTrigger in cardScripts:
#        if card._id not in queueTargets(card._id, skillTrigger):
#            continue
#        if checkConditions(card, skillTrigger.get("condition", {}), card._id)[0] == False:
#            continue
        skill = skillTrigger["skill"]
        value = eval(skillTrigger["value"])
        if skill == "all": ## Special case for abilities that boost all skills equally, and are listed as 'skills' or 'difficulty'
            allSkillsValue += value
        else:
            for baseSkill in skill:
                if baseSkills[baseSkill]: ## add value to existing skill
                    baseSkills[baseSkill] += value
                else: ## Add the skill if the card doesn't already have a base for it
                    baseSkills[baseSkill] = value
    ## Apply mission- and turn-duration boosts from storedCards dict
    if card in table and card._id in storedCards: ##only cards on the table are checked for boosts
        for boost in storedCards[card._id].get("m", []) + storedCards[card._id].get("t", []):
            boostSkill = skillDict[boost[0]]
            boostValue = boost[1]
            boostOrigin = boost[2]
            if boostOrigin not in [None, "boost"] and Card(boostOrigin) not in table: ## skip if the originating card isn't in play anymore
                continue
            if boostSkill == "all":## Special case for abilities that boost all skills equally, and are listed as 'skills' or 'difficulty'
                allSkillsValue += boostValue
            else:
                if baseSkills[boostSkill]:## add value to existing skill
                    baseSkills[boostSkill] += boostValue
                else: ## Add the skill if the card doesn't already have a base for it
                    baseSkills[boostSkill] = boostValue
    #### apply 'all skills' boosts
    for baseSkill in baseSkills.keys():
        if baseSkills[baseSkill] != None: ## Only apply the skill change if the character has the skill, skip otherwise
            baseSkills[baseSkill] += allSkillsValue
    return baseSkills

def passturn(group, x = 0, y = 0):
    mute()
    #### Make sure the queue is empty first
    global storedQueue
    if len(storedQueue) > 0: ## if the queue's not empty
        if storedQueue[0][4] != me._id: # Skip if you don't have priority on the active queue
            whisper("Cannot pass: you don't have priority.")
            return
        if storedQueue[0][5] == True: # If the queue is skippable:
            del storedQueue[0]
            notify("{} doesn't select a card.".format(me))
            setGlobalVariable("cardqueue", str(storedQueue))
            cleanup()
            queueSwitchPhases()
            return
        whisper("Cannot pass: There are mandatory abilities to resolve.")
        return
    global storedPhase
    phase = getGlobalVariable("phase")
    if phase == "mis.main":
        priority = eval(getGlobalVariable("priority"))
        if Player(priority[0]) != me:
            whisper("Cannot pass turn: You don't have priority.")
            return
        global storedQueue
        if len(storedQueue) > 0:
            whisper("Cannot pass priority: There are abilities that need resolving.")
            return
        if priority[1] == False:
            notify("{} passes.".format(me))
            cleanup()
            setGlobalVariable("priority", str((getPlayers()[1]._id, True)))
        else:
            notify("{} passes, enters Mission Resolution.".format(me))
            setGlobalVariable("priority", str((turnPlayer()._id, False)))
            setGlobalVariable("phase", "mis.res")

def queueTargets(qCard = None, params = None, qSource = None):
    mute()
    global storedQueue, storedCards
    if qCard == None and params == None:
        if storedQueue == []:
            return []
        (qCard, qTrigger, qType, qCount, qPriority, qSkippable, qSource) = storedQueue[0]
        if qTrigger in ["game", "res"]:
            return qCard
        action, params = scriptsDict[Card(qCard).model][qType][int(qTrigger)]
    targetDict = params.get("target", None)
    if targetDict == None:
        return []
    if targetDict == 'self':
        return [qCard]
    if targetDict == 'source':
        return [qSource]
    if targetDict == "stored":
        return storedCards[qCard].get("st", [])
    ####Get targets
    targets = [c for c in storedCards
         if checkConditions(Card(c), targetDict, qSource)[0] == True
        ]
    if targetDict.get("ignoreSelf", False) and qSource in targets:
        targets.remove(qSource)
    return targets

def phaseTriggers(triggerName, sourceId, skippable = False):
    mute()
    global storedCards, storedQueue
    heroTriggers = []
    villainTriggers = []
    newQueue = []
    for c in storedCards:
        card = Card(c)
        if card in table and cardActivity(card) in ["active", "active mission"] and hasTriggers(card, triggerName, sourceId):
            if card.controller == me:
                heroTriggers.append(c)
            else:
                villainTriggers.append(c)
    if len(villainTriggers) == 0 and heroTriggers == [sourceId]: ## Don't queue if the only trigger is the source
        return triggerScripts(Card(sourceId), triggerName, sourceId)
    if len(heroTriggers) > 0: ## attach hero triggers to queue
        newQueue += [(heroTriggers, "game", triggerName, len(heroTriggers), turnPlayer()._id, skippable, sourceId)]
    if len(villainTriggers) > 0: ## attach villain triggers to queue
        newQueue += [(villainTriggers, "game", triggerName, len(villainTriggers), turnPlayer(False)._id, skippable, sourceId)]
    if len(newQueue) == 0: ## skip all this junk if there's no actual triggers
        return []
    notify("{} has {} triggers to resolve.".format(me if len(heroTriggers) > 0 else turnPlayer(False), triggerName))
    return newQueue

def hasTriggers(card, triggerName, sourceId):
    mute()
    if sourceId == None:
        sourceId = card._id
    if triggerName not in scriptsDict.get(card.model, []): #return false if the card doesn't have any trigger
        return False
    for (trigger, params) in scriptsDict[card.model].get(triggerName, []): #Check each trigger to see if it is valid
#        if sourceId != card._id and eval(params.get("trigger", "False")) == False:
#            continue
        if checkConditions(card, params.get("condition", {}), sourceId)[0] == False:
            continue
        if 'trigger' in params: ## Check if the ability triggers off another card
            if checkConditions(Card(sourceId), params["trigger"], card._id)[0] == False:
                continue ## Skip the card if it doesn't match specific trigger conditions
        else:
            if card._id != sourceId:
                continue
        return True
    return False

def checkConditions(card, conditions, sourceId):
    mute()
    global storedCards, storedMission
    if cardActivity(card) == "inactive":
        return (False, "Inactive")
    if not eval(conditions.get("custom", 'True')):
        return (False, "State")
    glyphCheck = conditions.get("glyph", [])
    if glyphCheck != [] and not hasGlyph(storedCards[card._id].get("g", []), glyphCheck):
        return (False, "Glyph")
    statusCheck = conditions.get("status", [])
    if statusCheck != [] and storedCards[card._id]["s"] not in statusCheck:
        return (False, "Status")
    skillCheck = conditions.get("hasSkill", None)
    if skillCheck != None and getStats(card)[skillCheck] != None:
        return (False, "Skill")
    typeCheck = conditions.get("type", [])
    if typeCheck != [] and not card.Type in typeCheck:
        return (False, "Type")
    nameCheck = conditions.get("cardName", [])
    if nameCheck != [] and not card.Name in nameCheck:
        return (False, "Name")
    return (True, None)

def triggerScripts(card, type, sourceId): ## note this function assumes that the card scripts exist, doesn't do any verifying
    mute()
    if not hasTriggers(card, type, sourceId):
        return []
    cardScripts = scriptsDict[card.model][type]
    global storedCards
    queue = []
    scriptIndex = -1
    for (actionType, params) in cardScripts:
        scriptIndex += 1
        ## Verify that the condition is met
        if checkConditions(card, params.get("condition", {}), sourceId)[0] == False:
            continue #### Skip this trigger if the condition wasn't met    
        if actionType == "moveCard":
            targetCheck = params.get("target", {})
            fromGroup = eval(targetCheck["group"])
            if fromGroup == me.Deck:
                me.Deck.setVisibility('me')
                rnd(1,10)
            skillCheck = targetCheck.get("hasSkill", None)
            typeCheck = targetCheck.get("type", [])
            targets = [c for c in fromGroup
                    if (typeCheck == [] or c.Type in typeCheck)
                    and (skillCheck == None or getStats(c)[skillCheck] != None)
                    ]
            if len(targets) == 0: ## Don't bother running the script if the list is empty
                continue
            count = eval(params.get("count", "0"))
            choices = []
            while count > 0 and len(targets) > 0:
                choice = askCard(targets)
                if choice == None: ## If the player closes the window
                    if params.get("skippable", False) == False: #when a choice is required
                        continue
                    else:
                        break
                choices.append(choice)
                targets.remove(choice)
                count -= 1
            toGroup = eval(params["to"][0])
            toIndex = params["to"][1]
            doShuffle = False
            if toIndex == "shuffle":
                toIndex = 0
                doShuffle = True            
            for c in choices:
                notify("{} moves {} to {} from {}.".format(me, choice, toGroup.name, fromGroup.name))
                c.moveTo(toGroup, toIndex)
            if fromGroup == me.Deck or (toGroup == me.Deck and doShuffle == True): ## Shuffle the deck after looking at it
                me.Deck.setVisibility('none')
                rnd(1,10)
                me.Deck.shuffle()
            continue
        elif actionType == "ruleSet":
            rule = params["rule"]
            value = eval(params["value"])
            global storedGameStats
            storedGameStats[rule] = (value, card._id)
            setGlobalVariable("gameStats", str(storedGameStats))
            continue
        elif actionType == "powerChange":
            if params["player"] == "hero":
                player = turnPlayer()
            else:
                player = turnPlayer(False)
            powerNum = eval(params["value"])
            if player.Power + powerNum < 0: ## if the player doesn't have enough power to pay
                player.Power = 0
                powerNum = player.Power
            else:
                player.Power += powerNum
            notify("{} {} {} power from {}.".format(player, "loses" if powerNum < 0 else "gains", powerNum, card))
            continue
        elif actionType == "fillHand":
            if params["player"] == "hero":
                player = turnPlayer()
            else:
                player = turnPlayer(False)
            count = fillHand(eval(params["value"]))
            notify("{} refilled hand to 8, drawing {} cards.".format(me, count))
            continue
        elif actionType == "discard":
            if params["player"] == "hero":
                player = turnPlayer()._id
            else:
                player = turnPlayer(False)._id
            targetCount = eval(params["count"])
            if targetCount > 0:
                queue.append((card._id, scriptIndex, type, targetCount, player, params.get("skippable", False), sourceId))
                notify("{} must choose and discard {} card{}.".format(Player(player), targetCount, "" if targetCount == 1 else "s"))
            continue
        #### The rest of these actions may use the queue
        ## Acquire the targets for whatever action it may use
        targets = queueTargets(card._id, params, sourceId)
        targetCheck = params.get("targets", None)
        targetCount = params.get("count", "all")
        if targetCheck in ["this", "stored"] or targetCount == "all": ## These don't use the queue
            if actionType == "statusChange":
                action = params["action"]
                for target in targets:
                    if action == "store":
                        if "st" in storedCards[target]:
                            storedCards[target]["st"] += [target]
                        else:
                            storedCards[target]["st"] = [target]
                    elif action == "stop":
                        storedCards[target]["s"] = "s"
                        notify("{} stops {}'s {}.".format(card, me, Card(target)))
                    elif action == "block":
                        blockedCards = storedCards[target].get("b", [])
                        if params.get("ignoreBlockAssign", False):
                            storedCards[target]["b"] = blockedCards + [None]
                        else:
                            storedCards[target]["b"] = blockedCards + [card._id]
                        notify("{} blocks {}'s {}.".format(card, me, Card(target)))
                    elif action == "ready":
                        storedCards[target]["s"] = "r"
                        if "b" in storedCards[target]:
                            del storedCards[target]["b"]
                        notify("{} readies {}'s {}.".format(card, me, Card(target)))
                    elif action == "assign":
                        storedCards[target]["s"] = "a"
                        notify("{} assigns {}'s {}.".format(card, me, Card(target)))
                    elif action == "incapacitate":
                        storedCards[target]["s"] = "i"
                        notify("{} incapacitates {}'s {}.".format(card, me, Card(target)))
                    elif action == "destroy":
                        Card(target).setController(Card(target).owner)
                        del storedCards[target]
                        remoteCall(Card(target).owner, "remoteMove", [Card(target), 'Discard'])
                        notify("{} destroys {}'s {}.".format(card, me, Card(target)))
                    else:
                        whisper("ERROR: action {} not found!".format(action))
            elif actionType == "skillChange":
                for target in targets:
                    duration = params["duration"]
                    if params.get("ignoreSource", False): ## True if the skill change is permanent after the source is gone
                        source = None
                    else:
                        source = card._id
                    skillBoosts = storedCards[target].get(duration, []) ##gets list of card's current skill changes for that duration
                    for skillType in params["skill"]:
                        skillBoosts += [(skillDict[skillType], eval(params["value"]), source)]
                    storedCards[target][duration] = skillBoosts
            elif actionType == "tagSet":
                for target in targets:
                    duration = params.get("duration", "p")
                    if params.get("ignoreSource", False):
                        source = None
                    else:
                        source = card._id
                    storedCards[target][params["tag"]] = (eval(params["value"]), source, duration)
            else:
                continue
            setGlobalVariable("cards", str(storedCards))
            cleanup()
            continue
        #### add trigger to card queue
        else:
            targetCount = eval(params.get("count", "0"))
            if len(targets) == 0 or targetCount <= 0: ## Skip this loop if there are no legal targets to choose
                continue
            if params["player"] == "hero":
                player = turnPlayer()._id
            else:
                player = turnPlayer(False)._id
            queue.append((card._id, scriptIndex, type, targetCount, player, params.get("skippable", False), sourceId))
    return queue
    
def addToQueue(queue):
    if queue != []: ## Only update cardqueue if there are changes to be made
        global storedQueue
        storedQueue = queue + storedQueue
        setGlobalVariable("cardqueue", str(storedQueue))
    return storedQueue

def cleanTable(group, x = 0, y = 0):
    mute()
    cleanup()

def cleanup(remote = False):
    mute()
    if turnPlayer().hasInvertedTable():
        invert = True
    else:
        invert = False
    missionSkill, missionDiff, failcount, compcount, glyphwin, expwin, villwin = (0, 0, 0, 0, 0, 0, 0)
    alignvars = {"a": 0, "r": 0, "s": 0, "va": 0, "vr": 0, "vs": 0}
    global storedCards, storedQueue
    if len(storedQueue) > 0 and len(storedQueue[0]) > 0:
#        actionQueue = storedQueue[0][3]
        actionQueue = queueTargets()
        if storedQueue[0][4] == turnPlayer()._id:
            actionColor = HeroActionColor
        elif storedQueue[0][4] == turnPlayer(False)._id:
            actionColor = VillainActionColor
        else:
            actionColor = None
    else:
        actionQueue = []
    #### Get the active mission's data
    if storedMission != None:
        mission = Card(storedMission[0])
        type = storedMission[1]
        status = storedMission[2]
        value = getStats(mission)[type]
#    #### Scan the table for cards that shouldn't belong there
#    for card in table:
#        if card._id not in storedCards and card != mission:
#            notify("ERROR: {}'s {} did not enter play properly.".format(card.controller, card))
    #### Start aligning the cards on the table
    for c in sorted(storedCards.items(), key=lambda x: x[1]["#"]):
        c = c[0]
        card = Card(c)
        status = storedCards[c]["s"]
        if card.controller == me:
            if card not in table: ## If for some reason the card is no longer on the table, move it back
                if status == "c":
                    card.moveToTable(0,0, True)
                else:
                    card.moveToTable(0,0)
            if c in actionQueue:  ## add highlight for cards in the action queue
                if card.highlight != actionColor:
                    card.highlight = actionColor
            else:
                if card.highlight != None:
                    card.highlight = None
        if status == "am": ## skip general alignment of the active mission
            continue
        if not cardActivity(card) == "inactive":
            if card.controller == me:
                if status == "c" and card.isFaceUp == True: ## fix face-up complications
                    card.isFaceUp = False
                if status != "c" and card.isFaceUp == False: ## fix face-down cards that are supposed to be face-up
                    card.isFaceUp = True
                if status in ["i", "g"] or "b" in storedCards[c]:  ## rotate all cards that are blocked, incapacitated, or glyphs
                    if card.orientation != Rot90:
                        card.orientation = Rot90
                else:
                    if card.orientation != Rot0:
                        card.orientation = Rot0
            if status == "g": ## Skip direct alignment of earned glyphs
                for marker in card.markers:
                    if card.markers[marker] > 0:
                        card.markers[marker] = 0
                continue                
            #### Prep Failed Missions
            if status == "f" and card.Type == "Mission":
                xpos = (-79 if invert else -101) - 20 * failcount
                ypos = (-145 - 10 * failcount) if invert else (60 + 10 * failcount)
                failcount += 1
                if card.controller == me and card.position != (xpos, ypos):
                    card.moveToTable(xpos, ypos)
                for marker in card.markers:
                    if card.markers[marker] > 0:
                        card.markers[marker] = 0
            #### Prep Complications
            elif status == "c":
                xpos = (-79 if invert else -81) - 20 * compcount
                ypos = (70 + 10 * compcount) if invert else (-155 - 10 * compcount)
                compcount += 1
                missionDiff += 1
                if card.controller == me and card.position != (xpos, ypos):
                    card.moveToTable(xpos, ypos)
            else:
                cardSkills = getStats(card)
                #### Prep Hero cards
                if card.Type in heroTypes:
                    if status == "a":
                        countType = "a"
                        ypos = -98 if invert else 10
                        if storedMission != None and cardSkills[type] != "":
                            missionSkill += cardSkills[type]
                    elif status == "r":
                        countType = "r"
                        ypos = -207 if invert else 119
                    else:
                        countType = "s"
                        ypos = -316 if invert else 228
                #### Prep Villain Cards
                elif card.Type in villainTypes:
                    if status == "a":
                        countType = "va"
                        ypos = 10 if invert else -98
                        if storedMission != None and cardSkills[type] != "":
                            missionDiff += cardSkills[type]
                    elif status == "r":
                        countType = "vr"
                        ypos = 119 if invert else -207
                    else:
                        countType = "vs"
                        ypos = 228 if invert else -316
                xpos = alignvars[countType]
                invertxpos = alignvars[countType]
                #### Align the card
                glyphs = storedCards[c].get("g", [])
                invertxpos += 14*len(glyphs)
                if len(glyphs) > 0:
                    invertxpos += 12
                if card.orientation == Rot90:
                    invertxpos += 14 if len(glyphs) > 0 else 26
                if card.controller == me:
                    if card.position != (invertxpos if invert else xpos, ypos):
                        card.moveToTable(invertxpos if invert else xpos, ypos)
                if len(glyphs) > 0 and card.orientation == Rot90:
                        xpos += 14
                        invertxpos -= 14
                for glyphID in glyphs:
                    glyph = Card(glyphID)
                    expwin += int(glyph.experience)
                    glyphwin += 1
                    if glyph.controller == me:
                        glyph.moveToTable(invertxpos if invert else xpos, ypos)
                        glyph.sendToBack()
                    invertxpos -= 14
                    xpos += 14
                if len(glyphs) > 0:
                    xpos += 12
                if card.orientation == Rot90 and len(glyphs) == 0:
                    alignvars[countType] = xpos + 90
                else:
                    alignvars[countType] = xpos + 64
                #### Add skill markers on the card to show its current values
                if card.controller == me and card.Type != "Mission":
                    if card.isFaceUp:
                        for cardSkill in ["Culture", "Science", "Combat", "Ingenuity"]:
                            skillValue = cardSkills[cardSkill]
                            if skillValue == None:
                                skillValue = 0
                            if card.markers[markerTypes[cardSkill]] != skillValue:
                                card.markers[markerTypes[cardSkill]] = skillValue
        #### Align inactive cards
        else:
            if card.controller == me and card.position != (-197, -44):
                card.moveToTable(-197, -44)
                if card.orientation != Rot0:
                    card.orientation = Rot0
            #### Remove all markers from inactive cards
            for marker in card.markers:
                if card.markers[marker] > 0:
                    card.markers[marker] = 0
    #### Align the active mission
    if storedMission != None:
        if myTurn():
            if mission.position != (-81 if invert else -105, -45 if invert else -44):
                mission.moveToTable(-81 if invert else -105, -45 if invert else -44)
            if mission.orientation != Rot90:
                mission.orientation = Rot90
            missionDiff += value
            mission.markers[markerTypes["skill"]] = missionSkill
            mission.markers[markerTypes["diff"]] = missionDiff
    #### Determine victory conditions
    me.counters["Glyph Win"].value = glyphwin
    if glyphwin >= 7:
        notify("{} has won through Glyph Victory (7 glyphs.)".format(me))
        #### GLYPHWIN
    me.counters["Experience Win"].value = expwin
    if expwin >= storedVictory:
        notify("{} has won through Experience Victory ({} points.)".format(me, expwin))
    for villain in me.piles["Villain Score Pile"]:
        villwin += int(villain.cost)
    me.counters["Villain Win"].value = villwin
    if villwin >= storedVictory:
        notify("{} has won through Villain Victory ({} points.)".format(me, villwin))
    if remote == False: ## We don't want to trigger a loop
        remoteCall(getPlayers()[1], "cleanup", [True])

def playComplication(card, x = 0, y = 0):
    mute()
    if myTurn():
        whisper("Cannot play {} as the Hero player.".format(card))
        return
    global storedPhase
    phase = storedPhase
    if phase != "mis.main":
        whisper("Cannot play {}: It's not the main mission phase.".format(card))
        return
    if not myPriority():
        whisper("Cannot play {}: You don't have priority.".format(card))
        return
    global storedQueue
    if len(storedQueue) > 0:
        whisper("Cannot play {}: There are abilities that need resolving.".format(card))
        return
    global storedCards
    cost = 1 ## base cost for complication
    for c in storedCards:
        if storedCards[c]["s"] == "c":
            cost += 1  ## Add 1 to the cost for each complication already in play
        else:
            for (actionType, params) in scriptsDict.get(Card(c).model, {}).get("onGetComplicationCost", []):
                if actionType == "costChange":
                    if checkConditions(Card(c), params.get("condition", {}), card._id)[0] == True:
                        cost += eval(params["value"])
    if me.Power < cost:
        whisper("You do not have enough Power to play that as a complication.")
        return
    storeNewCards([card], {"s": "c"})
    card.moveToTable(0,0, True)
    card.peek()
    me.Power -= cost
    notify("{} plays a complication.".format(me))
    cleanup()
    setGlobalVariable("priority", str((turnPlayer()._id, False)))



def remoteMove(card, pile):
    mute()
    card.moveTo(card.owner.piles[pile])

def assign(card, x = 0, y = 0):
    mute()
    if cardActivity(card) == "inactive":
        whisper("You cannot play {} during your {}turn.".format(card, "" if myTurn() else "opponent's "))
        return
    if card.Type not in ["Adversary", "Team Character", "Support Character"]:
        whisper("Cannot assign {}: It is not an assignable card type.".format(card))
        return
    global storedPhase
    phase = storedPhase
    if phase != "mis.main":
        whisper("Cannot assign {}: It's not the main mission phase.".format(card))
        return
    if not myPriority():
        whisper("Cannot assign {}: You don't have priority.".format(card))
        return
    if storedMission == None:
        whisper("Cannot assign {} as there is no active mission.".format(card))
        return
    global storedQueue
    if len(storedQueue) > 0:
        whisper("Cannot assign {}: There are abilities that need resolving.".format(card))
        return
    mission, type, value, status = storedMission
    if card.properties[type] == None or card.properties[type] == "":
        whisper("Cannot assign {}: Does not match the active mission's {} skill.".format(card, type))
        return
    global storedCards
    if card._id in storedCards:
        if storedCards[card._id]["s"] != "r":
            whisper("Cannot assign: {} is not Ready.".format(card))
            return
        storedCards[card._id]["s"] = "a"
        setGlobalVariable("cards", str(storedCards))
        cleanup()
        setGlobalVariable("priority", str((turnPlayer(False)._id, False)))
        notify("{} assigns {}.".format(me, card))
    else:
        notify("ERROR: {} not in cards global dictionary.".format(card))

def checkScripts(card, actionType):
    mute()
    if card.name in scriptsDict:
        cardScripts = scriptsDict[card.name]
        if actionType in cardScripts:
            script = cardScripts[actionType]
            
    return None

#---------------------------------------------------------------------------
# Scripting Functions
#---------------------------------------------------------------------------

def scriptDestroy(card):
    mute()


#---------------------------------------------------------------------------
# Table group actions
#---------------------------------------------------------------------------

def endquest(group, x = 0, y = 0):
    mute()
    myCards = (card for card in table
        if card.controller == me)
    for card in myCards:
        card.highlight = None
        card.markers[markerTypes["block"]] = 0
    notify("{} is ending the quest.".format(me))

def endturn(group, x = 0, y = 0):
    mute()
    myCards = (card for card in table
        if card.controller == me)
    for card in myCards:
        card.markers[markerTypes["stop"]] = 0
        card.markers[markerTypes["block"]] = 0
        card.highlight = None
        if card.orientation == rot180:
          card.orientation = rot90
          card.markers[markerTypes["stop"]] = 1
        else:
          card.orientation = rot0
    notify("{} ends their turn.".format(me))

def clearAll(group, x = 0, y = 0):
    notify("{} clears all targets and combat.".format(me))
    for card in group:
      card.target(False)
      if card.controller == me and card.highlight in [AttackColor, BlockColor]:
          card.highlight = None

def roll20(group, x = 0, y = 0):
    mute()
    n = rnd(1, 20)
    notify("{} rolls {} on a 20-sided die.".format(me, n))

def flipCoin(group, x = 0, y = 0):
    mute()
    n = rnd(1, 2)
    if n == 1:
        notify("{} flips heads.".format(me))
    else:
        notify("{} flips tails.".format(me))

#---------------------------------------------------------------------------
# Table card actions
#---------------------------------------------------------------------------

def ready(card, x = 0, y = 0):
    mute()
    global storedCards
    storedCards[card._id]["s"] = "r"
    if "b" in storedCards[card._id]:
        del storedCards[card._id]["b"]
    setGlobalVariable("cards", str(storedCards))
    cleanup()
    notify("{} readies {}.".format(me, card))

def block(card, x = 0, y = 0):
    mute()
    global storedCards
    storedCards[card._id]["b"] = [None]
    setGlobalVariable("cards", str(storedCards))
    cleanup()
    notify("{} blocks {} from the quest.".format(me, card))

def stop(card, x = 0, y = 0):
    mute()
    global storedCards
    storedCards[card._id]["s"] = "s"
    setGlobalVariable("cards", str(storedCards))
    cleanup()
    notify("{} stops {}.".format(me, card))

def incapacitate(card, x = 0, y = 0):
    mute()
    global storedCards
    storedCards[card._id]["s"] = "i"
    setGlobalVariable("cards", str(storedCards))
    cleanup()
    notify("{} KO's {}.".format(me, card))

def destroy(card, x = 0, y = 0):
    mute()
    global storedCards
    if card._id in storedCards:
        del storedCards[card._id]
    setGlobalVariable("cards", str(storedCards))
    src = card.group
    card.moveTo(me.Discard)
    if src == table:
      notify("{} destroys {}.".format(me, card))
    else:
      notify("{} discards {} from their {}.".format(me, card, src.name))

def flip(card, x = 0, y = 0):
    mute()
    if card.isFaceUp:
        notify("{} flips {} face down.".format(me, card))
        card.isFaceUp = False
    else:
        card.isFaceUp = True
        notify("{} morphs {} face up.".format(me, card))

def addMarker(card, x = 0, y = 0):
    mute()
    notify("{} adds a counter to {}.".format(me, card))
    card.markers[markerTypes["counter"]] += 1

def removeMarker(card, x = 0, y = 0):
    mute()
    addmarker = markerTypes["counter"]
    if addmarker in card.markers:
      card.markers[addmarker] -= 1
      markername = addmarker[0]
      notify("{} removes a counter from {}".format(me, card))

#---------------------------------------------------------------------------
# Group Actions
#---------------------------------------------------------------------------

def randomDiscard(group, x = 0, y = 0):
    mute()
    card = group.random()
    if card == None: return
    notify("{} randomly discards a card.".format(me))
    card.moveTo(me.Discard)

def draw(group, x = 0, y = 0):
    if len(group) == 0: return
    mute()
    group[0].moveTo(me.hand)
    notify("{} draws a card.".format(me))

def refill(group, x = 0, y = 0):
    if len(group) == 0: return
    mute()
    count = len(me.hand)
    count2 = 8 - count
    for c in group.top(count2): c.moveTo(me.hand)
    notify("{} refills hand, drawing {} cards.".format(me, count2))

def shuffle(group, x = 0, y = 0):
    group.shuffle()