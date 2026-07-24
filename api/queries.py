HEROES_QUERY = """
query {
  constants {
    heroes {
      id
      displayName
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

MATCH_DATE_QUERY = """
query($matchId: Long!) {
  match(id: $matchId) {
    id
    startDateTime
  }
}
"""
