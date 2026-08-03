HEROES_QUERY = """
query {
  constants {
    heroes {
      id
      displayName
      shortName
    }
  }
}
"""

RAMPAGES_QUERY = """
query($heroId: Short!, $bracketBasicIds: [RankBracketBasicEnum]!, $take: Int!) {
  heroStats {
    rampages(request: {
      heroId: $heroId
      bracketBasicIds: $bracketBasicIds
      take: $take
    }) {
      matchId
      steamAccountId
    }
  }
}
"""

LATEST_RAMPAGES_QUERY = """
query($heroId: Short!, $take: Int!) {
  heroStats {
    rampages(request: {
      heroId: $heroId
      take: $take
    }) {
      matchId
      steamAccountId
    }
  }
}
"""

MATCH_DATE_QUERY = """
query($matchId: Long!) {
  match(id: $matchId) {
    id
    startDateTime
  }
}
"""

HERO_STATS_WIN_WEEK_QUERY = """
query($bracketIds: [RankBracket]!) {
  heroStats {
    winWeek(bracketIds: $bracketIds) {
      heroId
      matchCount
      winCount
    }
  }
}
"""

LEADERBOARD_HERO_QUERY = """
query($heroIds: [Short]!, $bracketIds: [RankBracket]!, $take: Int!) {
  leaderboard {
    hero(request: {
      heroIds: $heroIds
      bracketIds: $bracketIds
      take: $take
    }) {
      steamAccountId
    }
  }
}
"""

PLAYER_MATCHES_QUERY = """
query($steamAccountId: Long!, $heroIds: [Short]!, $take: Int!) {
  player(steamAccountId: $steamAccountId) {
    matches(request: {
      heroIds: $heroIds
      take: $take
    }) {
      id
      startDateTime
      durationSeconds
    }
  }
}
"""
