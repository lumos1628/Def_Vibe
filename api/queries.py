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

# Cosecha diaria: rampages recientes con la fecha del match anidada.
# Nota: Stratz limita take a un máximo de 20 en este endpoint.
RECENT_RAMPAGES_QUERY = """
query($heroId: Short!, $take: Int!) {
  heroStats {
    rampages(request: {
      heroId: $heroId
      take: $take
    }) {
      matchId
      steamAccountId
      match {
        id
        startDateTime
      }
    }
  }
}
"""

PRO_PLAYERS_QUERY = """
query {
  constants {
    proSteamAccounts {
      id
      name
    }
  }
}
"""

# Cosecha diaria: partidas recientes de un lote de jugadores (máx 5 por llamada).
# Sin filtro de héroe: el héroe se resuelve leyendo players del match.
PRO_RECENT_MATCHES_QUERY = """
query($steamAccountIds: [Long]!, $startDateTime: Long, $take: Int!) {
  players(steamAccountIds: $steamAccountIds) {
    steamAccountId
    matches(request: {
      startDateTime: $startDateTime
      take: $take
    }) {
      id
      startDateTime
      players {
        steamAccountId
        heroId
      }
    }
  }
}
"""

# Cosecha diaria: partidas recientes de un lote de jugadores con un héroe concreto.
PLAYERS_HERO_MATCHES_QUERY = """
query($steamAccountIds: [Long]!, $startDateTime: Long, $heroIds: [Short]!, $take: Int!) {
  players(steamAccountIds: $steamAccountIds) {
    steamAccountId
    matches(request: {
      startDateTime: $startDateTime
      heroIds: $heroIds
      take: $take
    }) {
      id
      startDateTime
    }
  }
}
"""
