from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from datetime import datetime
import database
import sqlite3
import asyncio
import shutil
import os

from config import BOT_TOKEN, ADMIN_ID

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_outcome(score):
    home, away = map(int, score.split("-"))

    if home > away:
        return "home"
    elif home < away:
        return "away"
    else:
        return "draw"

@dp.message(CommandStart())
async def start_command(message: Message):

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT approved
        FROM users
        WHERE telegram_id=?
        """,
        (message.from_user.id,)
    )

    existing_user = cursor.fetchone()

    if existing_user:

        if existing_user[0] == 1:
            await message.answer(
                "✅ You are already registered and approved."
            )
        else:
            await message.answer(
                "⏳ Your registration is already pending admin approval."
            )

        conn.close()
        return

    cursor.execute(
        """
        INSERT INTO users
        (telegram_id, username, full_name)
        VALUES (?, ?, ?)
        """,
        (
            message.from_user.id,
            message.from_user.username,
            message.from_user.full_name
        )
    )

    conn.commit()
    conn.close()

    await bot.send_message(
        ADMIN_ID,
        f"🆕 New registration\n\n"
        f"Name: {message.from_user.full_name}\n"
        f"Username: @{message.from_user.username}\n"
        f"Telegram ID: {message.from_user.id}"
    )

    await message.answer(
        "🏆 Welcome to BJ Football Predictor!\n\n"
        "Registration received.\n"
        "Awaiting admin approval."
    )

@dp.message(Command("allpredictions"))
async def all_predictions(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT telegram_id, full_name
        FROM users
        WHERE approved=1
        ORDER BY full_name
        """
    )

    users = cursor.fetchall()

    cursor.execute(
        """
        SELECT id, team1, team2
        FROM matches
        ORDER BY id
        """
    )

    matches = cursor.fetchall()

    if not matches:
        conn.close()
        await message.answer("No matches available.")
        return

    text = "📋 All Predictions\n\n"

    for match_id, team1, team2 in matches:

        text += f"⚽ Match {match_id}: {team1} vs {team2}\n\n"

        for user_id, full_name in users:

            cursor.execute(
                """
                SELECT predicted_score
                FROM predictions
                WHERE user_id=? AND match_id=?
                """,
                (user_id, match_id)
            )

            prediction = cursor.fetchone()

            if prediction:
                score = prediction[0]
            else:
                score = "X"

            text += f"{full_name}: {score}\n"

        text += "\n"

    conn.close()

    await message.answer(text)

@dp.message(Command("predictions"))
async def match_predictions(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split()

    if len(parts) != 2:
        await message.answer(
            "Usage:\n/predictions MATCH_ID"
        )
        return

    match_id = int(parts[1])

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            users.full_name,
            predictions.predicted_score
        FROM predictions
        JOIN users
        ON users.telegram_id = predictions.user_id
        WHERE predictions.match_id=?
        AND users.approved=1
        ORDER BY users.full_name
    """, (match_id,))

    rows = cursor.fetchall()

    conn.close()

    if not rows:
        await message.answer(
            f"No predictions for Match {match_id}."
        )
        return

    text = f"⚽ Predictions for Match {match_id}\n\n"

    for name, score in rows:
        text += f"• {name}: {score}\n"

    await message.answer(text)

@dp.message(Command("summary"))
async def prediction_summary(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT telegram_id, full_name
        FROM users
        WHERE approved=1
        ORDER BY full_name
    """)

    users = cursor.fetchall()

    cursor.execute("""
        SELECT id, team1, team2
        FROM matches
        ORDER BY id
    """)

    matches = cursor.fetchall()

    if not matches:
        conn.close()
        await message.answer("No matches available.")
        return

    text = "📊 Prediction Summary\n\n"

    for match_id, team1, team2 in matches:

        missing_users = []
        received = 0

        for user_id, full_name in users:

            cursor.execute("""
                SELECT id
                FROM predictions
                WHERE user_id=? AND match_id=?
            """, (user_id, match_id))

            prediction = cursor.fetchone()

            if prediction:
                received += 1
            else:
                missing_users.append(full_name)

        text += (
            f"⚽ Match {match_id}: "
            f"{team1} vs {team2}\n\n"
        )

        text += (
            f"Predictions received: {received}\n"
        )

        text += (
            f"Missing predictions: "
            f"{len(missing_users)}\n"
        )

        if missing_users:

            text += "\nMissing:\n"


            for user in missing_users:
                text += f"• {user}\n"

        text += "\n"

    conn.close()

    await message.answer(text)


@dp.message(Command("leagueinfo"))
async def league_info(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE approved=1")
    approved = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE approved=0")
    pending = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE approved=-1")
    rejected = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM matches")
    matches = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM predictions")
    predictions = cursor.fetchone()[0]

    conn.close()

    await message.answer(
        f"📊 League Information\n\n"
        f"Users: {users}\n"
        f"Approved: {approved}\n"
        f"Pending: {pending}\n"
        f"Rejected: {rejected}\n"
        f"Matches: {matches}\n"
        f"Predictions: {predictions}"
    )

@dp.message(Command("users"))
async def users_list(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT full_name, approved
        FROM users
        ORDER BY full_name
        """
    )

    rows = cursor.fetchall()

    conn.close()

    if not rows:
        await message.answer("No users found.")
        return

    text = "👥 Users\n\n"

    for name, approved in rows:

        if approved == 1:
            status = "✅"

        elif approved == -1:
            status = "❌"

        else:
            status = "⏳"

        text += f"{status} {name}\n"

    await message.answer(text)


@dp.message(Command("pending"))
async def pending_users(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT telegram_id, full_name
        FROM users
        WHERE approved=0
        """
    )

    users = cursor.fetchall()

    conn.close()

    if not users:
        await message.answer("No pending users.")
        return

    text = "⏳ Pending Users\n\n"

    for user in users:
        text += f"{user[1]} - {user[0]}\n"

    await message.answer(text)

@dp.message(Command("addmatch"))
async def add_match(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split()

    if len(parts) < 5:
        await message.answer(
            "Usage:\n"
            "/addmatch TEAM1 TEAM2 YYYY-MM-DD HH:MM\n\n"
            "Example:\n"
            "/addmatch Mexico SouthAfrica 2026-06-11 18:00"
        )
        return

    team1 = parts[1]
    team2 = parts[2]
    match_time = f"{parts[3]} {parts[4]}"

    try:
        datetime.strptime(match_time, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer(
            "❌ Invalid date format.\n"
            "Use YYYY-MM-DD HH:MM"
        )
        return

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO matches
        (team1, team2, match_time)
        VALUES (?, ?, ?)
        """,
        (team1, team2, match_time)
    )

    conn.commit()
    conn.close()

    await message.answer(
        f"✅ Match added.\n\n"
        f"{team1} vs {team2}\n"
        f"🕒 Deadline: {match_time}"
    )

@dp.message(Command("deletematch"))
async def delete_match(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split()

    if len(parts) != 2:
        await message.answer(
            "Usage:\n/deletematch MATCH_ID"
        )
        return

    match_id = int(parts[1])

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM matches WHERE id=?",
        (match_id,)
    )

    conn.commit()
    conn.close()

    await message.answer(
        f"✅ Match {match_id} deleted."
    )


@dp.message(Command("matches"))
async def show_matches(message: Message):

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, team1, team2, match_time
        FROM matches
        ORDER BY id
        """
    )

    matches = cursor.fetchall()
 
    conn.close()

    if not matches:
        await message.answer("No matches available.")
        return

    
    text = "🏆 Football Matches\n\n"

    for match in matches:

        text += (
            f"{match[0]}. {match[1]} vs {match[2]}\n"
            f"🕒 Deadline: {match[3]}\n\n"
        )

    await message.answer(text)


@dp.message(Command("predict"))
async def predict_match(message: Message):

    cursor.execute(
        """
        SELECT value
        FROM settings
        WHERE key='predictions_blocked'
        """
    )

    setting = cursor.fetchone()

    if setting and setting[0] == "1":
        await message.answer(
            "❌ Predictions are currently blocked by the administrator."
        )
    conn.close()
    return


    cursor.execute(
        """
        SELECT match_time,
               result,
               prediction_blocked
        FROM matches
        WHERE id=?
        """,
        (match_id,)
    )

    match = cursor.fetchone()

    if match[2] == 1:
        await message.answer(
            "❌ Predictions are blocked for this match."
        )
        conn.close()
        return

    parts = message.text.split()

    if len(parts) != 3:
        await message.answer(
            "Usage:\n"
            "/predict MATCH_ID SCORE\n\n"
            "Example:\n"
            "/predict 1 2-1"
        )
        return

    try:
        match_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Invalid Match ID.")
        return

    score = parts[2]

    if "-" not in score:
        await message.answer(
            "❌ Invalid score format.\n\n"
            "Example:\n"
            "/predict 1 2-1"
        )
        conn.close()
        return



    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT value
        FROM settings
        WHERE key='predictions_blocked'
        """
    )

    setting = cursor.fetchone()

    if setting and setting[0] == "1":
        await message.answer(
            "🔒 Predictions are currently blocked by the administrator."
        )
        conn.close()
        return


    # Check approval
    cursor.execute(
        """
        SELECT approved
        FROM users
        WHERE telegram_id=?
        """,
        (message.from_user.id,)
    )

    user = cursor.fetchone()

    if not user or user[0] != 1:
        conn.close()
        await message.answer(
            "❌ Your account has not been approved yet."
        )
        return

    cursor.execute(
        """
        SELECT match_time, result, manually_open
        FROM matches
        WHERE id=?
        """,
        (match_id,)
    )

    match = cursor.fetchone()

    match_time = match[0]
    result = match[1]
    manually_open = match[2]

    if not match:
        conn.close()
        await message.answer("❌ Match not found.")
        return


    # Check if result already entered
    if result:
        conn.close()
        await message.answer(
            "❌ Predictions are closed for this match."
        )
        return


    # Check deadline
    deadline = datetime.strptime(
     match_time,
     "%Y-%m-%d %H:%M"
    )

    if datetime.now() > deadline and manually_open != 1:
      await message.answer(
        "❌ Prediction deadline has expired."
      )
    conn.close()
    return

    if datetime.now() > deadline and manually_open != 1:
        conn.close()
        await message.answer(
            "❌ Prediction deadline has expired."
        )
        return


    # Check existing prediction
    cursor.execute(
        """
        SELECT id
        FROM predictions
        WHERE user_id=? AND match_id=?
        """,
        (message.from_user.id, match_id)
    )

    existing = cursor.fetchone()

    if existing:

        cursor.execute(
            """
            UPDATE predictions
            SET predicted_score=?
            WHERE user_id=? AND match_id=?
            """,
            (
                score,
                message.from_user.id,
                match_id
            )
        )

        reply = (
            f"✅ Prediction updated!\n"
            f"Match {match_id}: {score}"
        )

    else:

        cursor.execute(
            """
            INSERT INTO predictions
            (user_id, match_id, predicted_score)
            VALUES (?, ?, ?)
            """,
            (
                message.from_user.id,
                match_id,
                score
            )
        )

        reply = (
            f"✅ Prediction saved!\n"
            f"Match {match_id}: {score}"
        )

        conn.commit()
        conn.close()

        await message.answer(reply)


@dp.message(Command("blockallpredictions"))
async def block_all_predictions(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE settings
        SET value='1'
        WHERE key='predictions_blocked'
        """
    )

    conn.commit()
    conn.close()

    await message.answer(
        "🔒 All predictions have been blocked."
    )

@dp.message(Command("unblockallpredictions"))
async def unblock_all_predictions(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE settings
        SET value='0'
        WHERE key='predictions_blocked'
        """
    )

    conn.commit()
    conn.close()

    await message.answer(
        "🔓 All predictions have been reopened."
    )

@dp.message(Command("blockprediction"))
async def block_prediction(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split()

    if len(parts) != 2:
        await message.answer(
            "Usage:\n/blockprediction MATCH_ID"
        )
        return

    try:
        match_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Invalid Match ID.")
        return

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id
        FROM matches
        WHERE id=?
        """,
        (match_id,)
    )

    if not cursor.fetchone():
        conn.close()
        await message.answer("❌ Match not found.")
        return

    cursor.execute(
        """
        UPDATE matches
        SET manually_open=0
        WHERE id=?
        """,
        (match_id,)
    )

    conn.commit()
    conn.close()

    await message.answer(
        f"🔒 Predictions blocked for Match {match_id}."
    )


@dp.message(Command("unblockprediction"))
async def unblock_prediction(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split()

    if len(parts) != 2:
        await message.answer(
            "Usage:\n/unblockprediction MATCH_ID"
        )
        return

    try:
        match_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Invalid Match ID.")
        return

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id
        FROM matches
        WHERE id=?
        """,
        (match_id,)
    )

    if not cursor.fetchone():
        conn.close()
        await message.answer("❌ Match not found.")
        return

    cursor.execute(
        """
        UPDATE matches
        SET manually_open=1
        WHERE id=?
        """,
        (match_id,)
    )

    conn.commit()
    conn.close()

    await message.answer(
        f"🔓 Predictions reopened for Match {match_id}."
    )


@dp.message(Command("resetleague"))
async def reset_league(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    backup_name = (
        f"backup_"
        
    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    )

    shutil.copy(
        "beabjoel.db",
        backup_name
    )

    cursor.execute("DELETE FROM matches")
    cursor.execute("DELETE FROM predictions")
    cursor.execute("DELETE FROM scores")
    cursor.execute("DELETE FROM users")

    conn.commit()
    conn.close()

    await message.answer(
        "✅ League completely reset.\n"
        "All users must register again."
    )


@dp.message(Command("approve"))
async def approve_user(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split()

    if len(parts) != 2:
        await message.answer(
            "Usage:\n/approve TELEGRAM_ID"
        )
        return

    telegram_id = int(parts[1])

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET approved=1 WHERE telegram_id=?",
        (telegram_id,)
    )

    conn.commit()
    conn.close()

    await message.answer(
        f"User {telegram_id} approved."
    )

    try:
        await bot.send_message(
            telegram_id,
              "🎉 Congratulations!\n\n"
        "Your registration has been approved.\n"
        "You can now submit predictions."
        )
    except:
        pass

    def get_outcome(score):
      home, away = map(int, score.split("-"))

    if home > away:
        return "home"
    elif home < away:
        return "away"
    else:
        return "draw"



@dp.message(Command("approveall"))
async def approve_all(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET approved=1 WHERE approved=0"
    )

    count = cursor.rowcount

    conn.commit()
    conn.close()

    await message.answer(
        f"✅ Approved {count} users."
    )


@dp.message(Command("approved"))
async def approved_users(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT full_name, telegram_id
        FROM users
        WHERE approved=1
        ORDER BY full_name
        """
    )

    users = cursor.fetchall()
    conn.close()

    if not users:
        await message.answer("No approved users.")
        return

    text = "✅ Approved Users\n\n"

    for name, user_id in users:
        text += f"{name} - {user_id}\n"

    await message.answer(text)

@dp.message(Command("rejected"))
async def rejected_users(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT full_name, telegram_id
        FROM users
        WHERE approved=-1
        ORDER BY full_name
        """
    )

    users = cursor.fetchall()
    conn.close()

    if not users:
        await message.answer("No rejected users.")
        return

    text = "❌ Rejected Users\n\n"

    for name, user_id in users:
        text += f"{name} - {user_id}\n"

    await message.answer(text)

@dp.message(Command("editmatch"))
async def edit_match(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split()

    if len(parts) < 6:
        await message.answer(
            "Usage:\n"
            "/editmatch MATCH_ID TEAM1 TEAM2 YYYY-MM-DD HH:MM"
        )
        return

    match_id = int(parts[1])
    team1 = parts[2]
    team2 = parts[3]
    match_time = f"{parts[4]} {parts[5]}"

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE matches
        SET team1=?, team2=?, match_time=?
        WHERE id=?
        """,
        (team1, team2, match_time, match_id)
    )

    conn.commit()
    conn.close()

    await message.answer(
        f"✅ Match {match_id} updated."
    )

@dp.message(Command("matchresults"))
async def match_results(message: Message):

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT team1, team2, result
        FROM matches
        WHERE result IS NOT NULL
        """
    )

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await message.answer(
            "No results available."
        )
        return

    text = "⚽ Match Results\n\n"

    for team1, team2, result in rows:
        text += (
            f"{team1} {result} {team2}\n"
        )

    await message.answer(text)


@dp.message(Command("reject"))
async def reject_user(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split()

    if len(parts) != 2:
        await message.answer(
            "Usage:\n/reject USER_ID"
        )
        return

    user_id = int(parts[1])

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE users
        SET rejected=1,
            approved=0
        WHERE telegram_id=?
        """,
        (user_id,)
    )

    conn.commit()
    conn.close()

    try:
        await bot.send_message(
            user_id,
             "❌ Your registration request "
        "was rejected by the admin."
        )
    except:
        pass

    await message.answer(
        "❌ User rejected."
    )


@dp.message(Command("result"))
async def set_result(message: Message):

    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()

    if len(parts) != 3:
        await message.answer(
            "Usage:\n/result MATCH_ID SCORE"
        )
        return

    match_id = int(parts[1])
    actual_score = parts[2]

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT result FROM matches WHERE id=?",
        (match_id,)
    )

    match = cursor.fetchone()

    if not match:
        await message.answer("❌ Match not found.")
        conn.close()
        return

    if match[0]:
        conn.close()
        await message.answer(
            "❌ A result already exists for this match.\n\n"
            "Use /updateresult instead."
        )
        return
 
    cursor.execute(
        "UPDATE matches SET result=? WHERE id=?",
        (actual_score, match_id)
    )

    cursor.execute(
        "SELECT user_id, predicted_score FROM predictions WHERE match_id=?",
        (match_id,)
    )

    predictions = cursor.fetchall()

    for user_id, prediction in predictions:

        points = 0

        if get_outcome(prediction) == get_outcome(actual_score):
            points += 3

        if prediction == actual_score:
            points += 3

        cursor.execute(
            "INSERT OR IGNORE INTO scores (user_id, points) VALUES (?, 0)",
            (user_id,)
        )

        cursor.execute(
            "UPDATE scores SET points = points + ? WHERE user_id=?",
            (points, user_id)
        )

    conn.commit()

    cursor.execute(
       """
       SELECT users.full_name, scores.points
       FROM scores
       JOIN users
       ON users.telegram_id = scores.user_id
       ORDER BY scores.points DESC
       """
        )

    table_rows = cursor.fetchall()

    leaderboard = "🏆 Updated League Table\n\n"

    position = 1

    for name, points in table_rows:

       leaderboard += (
         f"{position}. {name} - "
         f"{points} pts\n"
       )

       position += 1

    conn.close()

    await message.answer(leaderboard)


@dp.message(Command("updateresult"))
async def update_result(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split()

    if len(parts) != 3:
        await message.answer(
            "Usage:\n/updateresult MATCH_ID SCORE"
        )
        return

    match_id = int(parts[1])
    new_result = parts[2]

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT result FROM matches WHERE id=?",
        (match_id,)
    )

    match = cursor.fetchone()

    if not match:
        conn.close()
        await message.answer("❌ Match not found.")
        return

    old_result = match[0]

    if not old_result:
        conn.close()
        await message.answer(
            "❌ No existing result.\nUse /result instead."
        )
        return

    # Remove previously awarded points
    cursor.execute(
        """
        SELECT user_id, predicted_score
        FROM predictions
        WHERE match_id=?
        """,
        (match_id,)
    )

    predictions = cursor.fetchall()

    for user_id, prediction in predictions:

        old_points = 0

        if get_outcome(prediction) == get_outcome(old_result):
            old_points += 3

        if prediction == old_result:
            old_points += 3

        cursor.execute(
            """
            UPDATE scores
            SET points = points - ?
            WHERE user_id=?
            """,
            (old_points, user_id)
        )

    # Update match result
    cursor.execute(
        """
        UPDATE matches
        SET result=?
        WHERE id=?
        """,
        (new_result, match_id)
    )

    # Award new points
    for user_id, prediction in predictions:

        new_points = 0

        if get_outcome(prediction) == get_outcome(new_result):
            new_points += 3

        if prediction == new_result:
            new_points += 3

        cursor.execute(
            """
            INSERT OR IGNORE INTO scores
            (user_id, points)
            VALUES (?, 0)
            """,
            (user_id,)
        )

        cursor.execute(
            """
            UPDATE scores
            SET points = points + ?
            WHERE user_id=?
            """,
            (new_points, user_id)
        )

    conn.commit()
    conn.close()

    await message.answer(
        f"✅ Result updated.\n\n"
        f"Match {match_id}\n"
        f"Old: {old_result}\n"
        f"New: {new_result}"
    )


@dp.message(Command("commands"))
async def commands_list(message: Message):

    await message.answer(
        "📋 Available Commands\n\n"
        "/start - Register\n"
        "/commands - View available commands\n"
        "/matches - View matches\n"
        "/predict - Submit prediction\n"
        "/mypredictions - View predictions\n"
        "/mypoints - View points\n"
        "/table - League table\n"
        "/matchresults - Match results\n"
        "/help - Help"
        "/rules - League rules"
    )

@dp.message(Command("broadcast"))
async def broadcast(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    reminder_text = message.text.replace(
        "/broadcast", ""
    ).strip()

    if not reminder_text:
        await message.answer(
            "Usage:\n/broadcast YOUR_MESSAGE"
        )
        return

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    # Total matches in league
    cursor.execute(
        "SELECT COUNT(*) FROM matches"
    )

    total_matches = cursor.fetchone()[0]

    if total_matches == 0:
        conn.close()

        await message.answer(
            "No matches available."
        )
        return

    # Approved users
    cursor.execute(
        """
        SELECT telegram_id, full_name
        FROM users
        WHERE approved=1
        """
    )

    users = cursor.fetchall()

    sent = 0

    for user_id, name in users:

        cursor.execute(
            """
            SELECT COUNT(DISTINCT match_id)
            FROM predictions
            WHERE user_id=?
            """,
            (user_id,)
        )

        predicted_matches = cursor.fetchone()[0]

        if predicted_matches < total_matches:

            missing = (
                total_matches
                - predicted_matches
            )

            try:
                await bot.send_message(
                    user_id,
                    f"⏰ Prediction Reminder\n\n"
                    f"{reminder_text}\n\n"
                    f"You still have "
                    f"{missing} match(es) "
                    f"without predictions."
                )

                sent += 1

            except:
                pass

    conn.close()

    await message.answer(
        f"✅ Reminder sent to {sent} user(s)."
    )

@dp.message(Command("unapprove"))
async def unapprove_user(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split()

    if len(parts) != 2:
        await message.answer(
            "Usage:\n/unapprove USER_ID"
        )
        return

    user_id = int(parts[1])

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE users
        SET approved=0
        WHERE telegram_id=?
        """,
        (user_id,)
    )

    conn.commit()
    conn.close()

    await message.answer(
        f"User {user_id} moved back to pending."
    )




@dp.message(Command("table"))
async def league_table(message: Message):

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT users.full_name, scores.points
        FROM scores
        JOIN users
        ON users.telegram_id = scores.user_id
        ORDER BY scores.points DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    if not rows:
        await message.answer("No scores yet.")
        return

    text = "🏆 BJ League Table\n\n"

    medals = ["🥇", "🥈", "🥉"]

    position = 1

    for name, points in rows:

        if position <= 3:
            icon = medals[position - 1]
        else:
            icon = f"{position}."

        text += f"{icon} {name} - {points} pts\n"

        position += 1

    await message.answer(text)

@dp.message(Command("help"))
async def help_command(message: Message):

    text = (
        "🏆 BJ Football Predictor Help\n\n"

        "How to Play:\n"
        "1. Register using /start\n"
        "2. Wait for admin approval\n"
        "3. View available matches using /matches\n"
        "4. Submit predictions using:\n"
        "   /predict MATCH_ID SCORE\n"
        "   Example: /predict 1 2-1\n"
        "5. Check your predictions using /mypredictions\n"
        "6. Check your points using /mypoints\n"
        "7. View the league table using /table\n\n"

        "User Commands:\n"
        "/start - Register for the league\n"
        "/matches - View available matches\n"
        "/predict - Submit or update a prediction\n"
        "/mypredictions - View your predictions\n"
        "/mypoints - View your points\n"
        "/table - View league standings\n"
        "/matchresults - View completed match results\n"
        "/rules - View league rules\n"
        "/help - Show this help message\n\n"

        "Important:\n"
        "• Predictions must be submitted before the match deadline.\n"
        "• Predictions cannot be changed after the deadline.\n"
        "• Points are awarded according to the league rules."
    )

    await message.answer(text)


@dp.message(Command("rules"))
async def rules_command(message: Message):

    text = (
        "📜 BJ Football Predictor – Rules and Regulations\n\n"

        "🏅 Eligibility\n\n"

        "1. Participants must be 21 years of age or older.\n"
        "2. Participants must be members of the BJ Football Predictor group.\n"
        "3. To join the group, click the link https://t.me/BeabJoelPredictor .\n\n"

        "📝 Registration and Approval\n\n"

        "1. To be approved by the administrator, each participant must deposit for each league competition.\n"
        "2. Account details for payment will be provided only by the administrator and posted on BJ Football Predictor group.\n\n"

        "⚠️ Important:\n"
        "Do not send money to any account unless you are officially instructed to do so by the administrator.\n\n"

        "⚽ Prediction and Scoring System\n\n"

        "1. Each league competition will consist of three or more matches.\n"
        "2. Participants must predict the exact score of each match before the deadline.\n"
        "3. All deadlines use East African Time.\n"
        "4. All participants and their predictions will be posted on BJ Football Predictor group after the prediction deadline.\n"
        "5. Points are awarded as follows:\n"
        "   • 6 points for predicting the exact score correctly.\n"
        "   • 3 points for correctly predicting the match outcome but not the exact score.\n"
        "   • 0 points for an incorrect prediction.\n\n"

        "6. Total points earned across all matches determine each participant's final score.\n\n"

        "🏆 Winner and Prize\n\n"

        "1. The participant with the highest total points at the end of the competition will be declared the winner.\n"
        "2. The winner will receive a prize equal to 200 ETB multiplied by the total number of participants.\n"
        "3. If two or more participants finish with the same highest score, the prize money will be divided equally among them.\n"
        "4. Winners and league standing will be announced in BJ Football Predictor group.\n"
        "5. Winners may choose their preferred account for prize transfer."
    )

    await message.answer(text)


@dp.message(Command("mypredictions"))
async def my_predictions(message: Message):

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT match_id, predicted_score
        FROM predictions
        WHERE user_id=?
        ORDER BY match_id
    """, (message.from_user.id,))

    rows = cursor.fetchall()

    conn.close()

    if not rows:
        await message.answer("No predictions yet.")
        return

    text = "📋 Your Predictions\n\n"

    for match_id, score in rows:
        text += f"Match {match_id}: {score}\n"

    await message.answer(text)


@dp.message(Command("backups"))
async def list_backups(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    backups = sorted(
        [
            f for f in os.listdir(".")
            if f.startswith("backup_")
            and f.endswith(".db")
        ],
        reverse=True
    )

    if not backups:
        await message.answer(
            "No backups found."
        )
        return

    text = "📂 Available Backups\n\n"

    for backup in backups[:10]:
        text += f"{backup}\n"

    await message.answer(text)

@dp.message(Command("restorelast"))
async def restore_last_backup(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    backups = [
        f for f in os.listdir(".")
        if f.startswith("backup_") and f.endswith(".db")
    ]

    if not backups:
        await message.answer(
            "❌ No backup files found."
        )
        return

    latest_backup = max(
        backups,
        key=os.path.getmtime
    )

    try:

        shutil.copy(
            "beabjoel.db",
            "before_restore.db"
        )

        shutil.copy(
            latest_backup,
            "beabjoel.db"
        )

        await message.answer(
            f"✅ Database restored.\n\nBackup used:\n{latest_backup}"
        )

    except Exception as e:
        await message.answer(
            f"❌ Restore failed:\n{e}"
        )

@dp.message(Command("mypoints"))
async def my_points(message: Message):

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT points FROM scores WHERE user_id=?",
        (message.from_user.id,)
    )

    result = cursor.fetchone()

    conn.close()

    points = result[0] if result else 0

    await message.answer(
        f"🏆 You have {points} points."
    )


@dp.message(Command("deleteresult"))
async def delete_result(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split()

    if len(parts) != 2:
        await message.answer(
            "Usage:\n/deleteresult MATCH_ID"
        )
        return

    try:
        match_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Invalid Match ID.")
        return

    conn = sqlite3.connect("beabjoel.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT result FROM matches WHERE id=?",
        (match_id,)
    )

    match = cursor.fetchone()

    if not match:
        conn.close()
        await message.answer("❌ Match not found.")
        return

    old_result = match[0]

    if not old_result:
        conn.close()
        await message.answer("❌ No result found.")
        return

    cursor.execute(
        """
        SELECT user_id, predicted_score
        FROM predictions
        WHERE match_id=?
        """,
        (match_id,)
    )

    predictions = cursor.fetchall()

    for user_id, prediction in predictions:

        points = 0

        if get_outcome(prediction) == get_outcome(old_result):
            points += 3

        if prediction == old_result:
            points += 3

        cursor.execute(
            """
            UPDATE scores
            SET points = points - ?
            WHERE user_id=?
            """,
            (points, user_id)
        )

    cursor.execute(
        """
        UPDATE matches
        SET result=NULL
        WHERE id=?
        """,
        (match_id,)
    )

    conn.commit()
    conn.close()

    await message.answer(
        f"✅ Result deleted.\n\n"
        f"Match ID: {match_id}\n"
        f"Deleted Result: {old_result}"
    )




async def main():
    print("BeabJoel Bot is running...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())