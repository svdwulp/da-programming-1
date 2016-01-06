"""Blackjack

Multiplayer version of a simplified blackjack game.

Rules:
- cards are dealt from a single, shuffled deck of 52 standard 'playing cards'
- when the deck runs out, a fresh deck is shuffled and used
  (note: this entails a player can receive the same card twice,
  e.g. aces of spades, in a single round, but it still allows for
  some level of card counting)
- card values:
  - number cards have face value (2=2, 3=3, etc.)
  - face cards all count for 10
  - aces count for either 1 or 11, whichever is more favorable for the player
  - colors (hearts, diamonds, spades and clubs) are irrelevant while
    calculating hand value
- the game is played for a preset number of rounds
- each player will play for an individual win, loss or draw during each
  round of the game and:
  - gain 1 point for each round won
  - lose 1 point for each round lost
  - neither gain nor win a point for each round resulting in a draw
- each round runs as follows:
  - each player is dealt start hand of two cards, visible to everyone
  - the dealer is handed a start hand of two cards of which
    only the first is visible
  - in turns, each player plays the game:
    - the aim for the player is to reach a total hand value of 21,
      which results in an immediate win of the round
    - when a players hand value exceeds 21 (bust), the player immediately
      loses the round
    - while the players hand value is below 21, the player can choose to
      'hit' or 'stand':
        - when a player chooses to 'hit', another card is added to their hand
        - when a player chooses to 'stand', they receive no more cards
  - when all players have played their turns, if any player has chosen to
    'stand', the dealer will play their hand:
    - the dealer will start by revealing their second card
    - if the dealers hand value is below 21, the dealer will repeatedly add
      cards to their hand until their hand value exceeds 16
    - if the dealers hand exceeded 21 (bust), all 'standing' players win
    - if the dealer did not bust his hand:
      - a player wins if their hand value exceeds the dealers
      - a player draws if their hand value equals the dealers
      - a player loses if their hand value is below the dealers
"""
import random


card_symbols = (
    [str(i) for i in range(2, 11)] +
    list("JQKA")
)
card_values = dict(
    zip(
        card_symbols,
        [i for i in range(2, 11)] + [10, 10, 10, 11]
    )
)
card_colors = list("hdsc")


class Hand(list):
    def __init__(self, *args):
        list.__init__(self, *args)

    def calculate_value(self):
        values = []
        for symbol, color in self:
            values.append(card_values[symbol])
        while sum(values) > 21 and 11 in values:
            values[values.index(11)] = 1
        return sum(values)

    @classmethod
    def single_card_str(cls, card):
        return "{}{}".format(card[0], card[1])

    def __str__(self):
        return "[{}]".format(
            ", ".join(Hand.single_card_str(card) for card in self)
        )


class Player(object):
    def __init__(self, name, callback):
        self.name = name
        self.hand = Hand()
        self.points = 0
        self.callback = callback

    def decision(self, hand, dealer):
        try:
            decision = bool(self.callback("decision", (hand, dealer)))
        except:
            decision = False
        return decision

    def card_seen(self, player, card):
        self.callback("card_seen", (player, card))

    def message(self, msg):
        self.callback("message", (msg))

    def result(self, result):
        self.callback("result", (result))

    def __str__(self):
        return self.name


class Deck(list):
    def __init__(self, *args):
        list.__init__(self, *args)
        self.add_deck()

    def add_deck(self):
        self.extend([
            (value, color)
            for value in card_values
            for color in card_colors
        ])
        random.shuffle(self)

    def draw(self):
        if len(self) == 0:
            self.add_deck()
        return self.pop()


class Dealer(object):
    def __init__(self, players):
        self.name = "Dealer"
        self.deck = Deck()
        self.players = players
        self.hand = Hand()

    def show_card(self, player, card):
        for p in self.players:
            p.card_seen(player.name, self.hand.single_card_str(card))

    def draw(self, player, show_card=True):
        card = self.deck.draw()
        if show_card:
            self.show_card(player, card)
        return card

    def emit_message(self, msg):
        for player in self.players:
            player.message(msg)

    def reset_hands(self):
        self.hand = Hand()
        for player in self.players:
            player.hand = Hand()

    def play_round(self):
        self.emit_message("Round starts")
        self.reset_hands()
        # deal initial hand to all players and self
        for player in self.players:
            player.hand.append(self.draw(player))
        self.hand.append(self.draw(self))
        for player in self.players:
            player.hand.append(self.draw(player))
            self.emit_message("{} got {}".format(player.name, player.hand))
        # do not show second dealer card
        self.hand.append(self.draw(self, False))
        self.emit_message(
            "Dealer got {}".format(
                self.hand.single_card_str(self.hand[0])
            )
        )
        if self.play_all_players():
            self.play_dealer_hand()
        else:
            # reveal second dealer card when not playing
            self.show_card(self, self.hand[1])
        self.emit_message("Round ends")

    def play_all_players(self):
        # play all players hands
        players_left = False
        for player in self.players:
            self.play_player(player)
            if player.hand.calculate_value() < 21:
                players_left = True
        return players_left

    def play_dealer_hand(self):
        self.emit_message("Dealer shows hand: {}".format(self.hand))
        self.show_card(self, self.hand[1])
        hand_value = self.hand.calculate_value()
        self.emit_message("Dealer hand value = {}".format(hand_value))
        while hand_value < 17:
            self.hand.append(self.draw(self))
            self.emit_message("Dealer hit, hand now: {}".format(self.hand))
            hand_value = self.hand.calculate_value()
            self.emit_message("Dealer hand value = {}".format(hand_value))
        if hand_value <= 21:
            self.emit_message("Dealer stands")
            for player in self.players:
                player_hand_value = player.hand.calculate_value()
                if player_hand_value >= 21:
                    continue
                if player_hand_value < hand_value:
                    self.do_player_lose(
                        player,
                        "dealer {} vs player {}".format(
                            hand_value, player_hand_value
                        )
                    )
                elif player_hand_value > hand_value:
                    self.do_player_win(
                        player,
                        "dealer {} vs player {}".format(
                            hand_value, player_hand_value
                        )
                    )
                else:
                    self.do_player_draw(
                        player,
                        "dealer {} vs player {}".format(
                            hand_value, player_hand_value
                        )
                    )
        else:
            self.emit_message("Dealer busted")
            for player in self.players:
                player_hand_value = player.hand.calculate_value()
                if player_hand_value >= 21:
                    continue
                self.do_player_win(player, "dealer busted")

    def do_player_win(self, player, reason=None):
        player.points += 1
        player.result("win")
        if reason:
            self.emit_message("{} wins (reason: {})".format(player, reason))
        else:
            self.emit_message("{} wins".format(player))

    def do_player_lose(self, player, reason=None):
        player.points -= 1
        player.result("loss")
        if reason:
            self.emit_message("{} loses (reason: {})".format(player, reason))
        else:
            self.emit_message("{} loses".format(player))

    def do_player_draw(self, player, reason=None):
        # player.points += 0
        player.result("draw")
        if reason:
            self.emit_message("{} draws (reason: {})".format(player, reason))
        else:
            self.emit_message("{} draws".format(player))

    def play_player(self, player):
        hand_value = player.hand.calculate_value()
        if hand_value == 21:
            self.do_player_win(player, "hit 21")
            return
        decision = player.decision(player.hand.copy(), self.hand[0])
        if not decision:
            self.emit_message("{} decided to stand".format(player))
        while decision:
            player.hand.append(self.draw(player))
            self.emit_message(
                "{} decided to hit, hand now: {}".format(
                    player, player.hand
                )
            )
            hand_value = player.hand.calculate_value()
            if hand_value == 21:
                self.do_player_win(player, "hit 21")
                return
            elif hand_value > 21:
                self.do_player_lose(player, "busted")
                return
            decision = player.decision(player.hand.copy(), self.hand[0])
            if not decision:
                self.emit_message("{} decided to stand".format(player))
        if hand_value == 21:
            self.do_player_win(player, "hit 21")
        elif hand_value > 21:
            self.do_player_lose(player, "busted")
