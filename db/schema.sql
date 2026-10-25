-- Relational schema for the league standings app (MariaDB).

CREATE TABLE league (
    league_id INT PRIMARY KEY AUTO_INCREMENT,
    name      VARCHAR(100) NOT NULL,
    country   VARCHAR(100) NOT NULL
);

CREATE TABLE club (
    club_id      INT PRIMARY KEY AUTO_INCREMENT,
    name         VARCHAR(100) NOT NULL UNIQUE,
    city         VARCHAR(100) NOT NULL,
    stadium_name VARCHAR(100) NOT NULL
);

CREATE TABLE season (
    season_year INT PRIMARY KEY,
    start_date  DATE NOT NULL,
    end_date    DATE NOT NULL,
    league_id   INT  NOT NULL,
    CONSTRAINT fk_season_league FOREIGN KEY (league_id) REFERENCES league (league_id),
    CONSTRAINT chk_season_dates CHECK (end_date > start_date)
);

-- Home and away club are stored directly on the match, so each role is explicit.
CREATE TABLE matches (
    match_id     INT PRIMARY KEY AUTO_INCREMENT,
    season_year  INT         NOT NULL,
    match_date   DATE        NOT NULL,
    home_club_id INT         NOT NULL,
    away_club_id INT         NOT NULL,
    home_score   INT         NOT NULL DEFAULT 0,
    away_score   INT         NOT NULL DEFAULT 0,
    match_status VARCHAR(20) NOT NULL DEFAULT 'scheduled',
    CONSTRAINT fk_match_season FOREIGN KEY (season_year) REFERENCES season (season_year),
    CONSTRAINT fk_match_home   FOREIGN KEY (home_club_id) REFERENCES club (club_id),
    CONSTRAINT fk_match_away   FOREIGN KEY (away_club_id) REFERENCES club (club_id),
    CONSTRAINT chk_match_clubs  CHECK (home_club_id <> away_club_id),
    CONSTRAINT chk_match_scores CHECK (home_score >= 0 AND away_score >= 0),
    CONSTRAINT chk_match_status CHECK (match_status IN ('scheduled', 'ongoing', 'completed'))
);

CREATE INDEX idx_matches_status_date ON matches (match_status, match_date);

-- One standings row per club and season.
CREATE TABLE season_stat (
    season_year    INT NOT NULL,
    club_id        INT NOT NULL,
    matches_played INT NOT NULL DEFAULT 0,
    wins           INT NOT NULL DEFAULT 0,
    draws          INT NOT NULL DEFAULT 0,
    losses         INT NOT NULL DEFAULT 0,
    points         INT NOT NULL DEFAULT 0,
    PRIMARY KEY (season_year, club_id),
    CONSTRAINT fk_stat_season FOREIGN KEY (season_year) REFERENCES season (season_year),
    CONSTRAINT fk_stat_club   FOREIGN KEY (club_id) REFERENCES club (club_id)
);
