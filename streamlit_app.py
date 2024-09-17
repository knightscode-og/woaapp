import streamlit as st
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from datetime import timezone, datetime, timedelta

# Load environment variables
load_dotenv()

# MongoDB connection string from .env
MONGO_URL = os.getenv("MONGO_URL")

# Connect to MongoDB
client = MongoClient(MONGO_URL)
db = client['workout_db']
workouts_collection = db['workouts']
exercises_collection = db['exercises']
exercise_log_collection = db['exercise_log']
workout_log_collection = db['workout_log']

# Sidebar for page selection (simulating routing)
page = st.sidebar.selectbox("Select Page", ["Home", "Create Exercise", "Create Workout"])

if page == "Home":
    # Function to get the previous weight and notes for an exercise
    def get_previous_log(exercise_id):
        previous_log = exercise_log_collection.find_one(
            {"exercise_id": exercise_id},
            sort=[("updated_ts", -1)]  # Sort by the latest timestamp
        )
        if previous_log:
            return previous_log.get('weight', ''), previous_log.get('notes', '')
        return '', ''

    # Function to auto-save logs (checks for logs created today)
    def save_exercise_log(exercise_id, today_weight, today_notes):
        current_time = datetime.now(timezone.utc)
        
        # Define the start and end of today for comparison
        start_of_today = datetime.combine(current_time.date(), datetime.min.time())
        end_of_today = start_of_today + timedelta(days=1)
        
        # Check if there's an existing log for this exercise from today
        existing_log = exercise_log_collection.find_one({
            "exercise_id": exercise_id,
            "created_ts": {"$gte": start_of_today, "$lt": end_of_today}  # Log created today
        })
        
        if existing_log:
            # Update existing log with today's data
            exercise_log_collection.update_one(
                {"_id": existing_log["_id"]},
                {"$set": {
                    "weight": today_weight,
                    "notes": today_notes,
                    "updated_ts": current_time
                }}
            )
        else:
            # Insert new log entry if no existing log is found for today
            exercise_log_collection.insert_one({
                "exercise_id": exercise_id,
                "weight": today_weight,
                "notes": today_notes,
                "created_ts": current_time,
                "updated_ts": current_time
            })

    # Dropdown to select workout
    st.title("🏋️ Workout Tracker")
    workouts = list(workouts_collection.find({}))
    workout_names = [workout['name'] for workout in workouts]
    selected_workout = st.selectbox("Select Workout", workout_names)

    if selected_workout:
        workout = workouts_collection.find_one({"name": selected_workout})
        
        st.header(f"🏋️ Workout: {workout['description']}")
        
        # For each exercise in the selected workout, show the form
        for exercise_info in workout['exercises']:
            exercise = exercises_collection.find_one({"_id": exercise_info['exercise_id']})

            # Create a container for each exercise, including inputs and save button
            with st.container():
                st.markdown("""
                    <style>
                    .exercise-container {
                        padding: 15px;
                        margin-bottom: 15px;
                        background-color: #f9f9f9;
                        border-radius: 10px;
                        border: 1px solid #ddd;
                    }
                    .exercise-header {
                        color: #4CAF50;
                        font-size: 20px;
                        font-weight: bold;
                    }
                    .exercise-details {
                        color: #666;
                    }
                    .save-button {
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        text-align: center;
                        text-decoration: none;
                        display: inline-block;
                        font-size: 14px;
                        margin: 4px 2px;
                        cursor: pointer;
                    }
                    </style>
                """, unsafe_allow_html=True)

                # Display all exercise details, inputs, and save button inside the same container
                st.markdown(f"""
                <div class='exercise-container'>
                    <div class='exercise-header'>{exercise['name']}</div>
                    <div class='exercise-details'>
                        <p>Description: {exercise['directions']}</p>
                        <p>Sets: {exercise_info['sets']}, Reps: {exercise_info['reps']}, RTE: {exercise_info['rte']}</p>
                        <p>Rest: {exercise['rest']} min</p>
                    </div>
                """, unsafe_allow_html=True)

                previous_weight, previous_notes = get_previous_log(exercise_info['exercise_id'])
                st.write(f"**Previous Notes:** {previous_notes}")
                st.write(f"**Previous Weight:** {previous_weight}")

                # Fields for today's workout input
                today_weight = st.text_input(f"Today's Weight for {exercise['name']}", key=f"weight_{exercise_info['exercise_id']}")
                today_notes = st.text_area(f"Today's Notes for {exercise['name']}", key=f"notes_{exercise_info['exercise_id']}")

                # Auto-save function after 5 seconds or losing focus
                if st.button(f"Save {exercise['name']}", key=f"save_{exercise_info['exercise_id']}"):
                    save_exercise_log(exercise_info['exercise_id'], today_weight, today_notes)

                st.markdown("</div>", unsafe_allow_html=True)  # Close the exercise container div
        
        workout_notes = st.text_area("🏋️ Workout Notes")
        
        # Submit workout
        if st.button("Submit Workout"):
            current_time = datetime.now(timezone.utc)
            workout_log_collection.insert_one({
                "workout_id": workout['_id'],
                "notes": workout_notes,
                "created_ts": current_time,
                "updated_ts": current_time
            })
            st.success("Workout submitted successfully!")

elif page == "Create Exercise":
    st.title("🏋️ Create New Exercise")

    # Form to create a new exercise
    exercise_name = st.text_input("Exercise Name")
    exercise_description = st.text_area("Exercise Description")
    exercise_muscle_group = st.text_input("Muscle Group (e.g., Chest, Arms, Legs)")
    exercise_rest = st.number_input("Rest Time (minutes)", min_value=0, step=1)
    
    if st.button("Save Exercise"):
        exercises_collection.insert_one({
            "name": exercise_name,
            "directions": exercise_description,
            "muscle_group": exercise_muscle_group,
            "rest": exercise_rest
        })
        st.success(f"Exercise '{exercise_name}' added successfully!")

elif page == "Create Workout":
    st.title("🏋️ Create New Workout")

    # Get a list of exercises to choose from
    exercises = list(exercises_collection.find({}))
    exercise_options = [exercise['name'] for exercise in exercises]
    
    workout_name = st.text_input("Workout Name")
    workout_description = st.text_area("Workout Description")
    
    selected_exercises = st.multiselect("Select Exercises for the Workout", exercise_options)

    # Exercise setup for the workout
    workout_exercises = []
    for exercise_name in selected_exercises:
        sets = st.number_input(f"Sets for {exercise_name}", min_value=1, step=1, key=f"sets_{exercise_name}")
        reps = st.number_input(f"Reps for {exercise_name}", min_value=1, step=1, key=f"reps_{exercise_name}")
        rte = st.number_input(f"RTE for {exercise_name}", min_value=1, max_value=10, step=1, key=f"rte_{exercise_name}")
        workout_exercises.append({
            "exercise_id": exercises_collection.find_one({"name": exercise_name})["_id"],
            "sets": sets,
            "reps": reps,
            "rte": rte
        })
    
    if st.button("Save Workout"):
        workouts_collection.insert_one({
            "name": workout_name,
            "description": workout_description,
            "exercises": workout_exercises
        })
        st.success(f"Workout '{workout_name}' created successfully!")

# Close the MongoDB connection
client.close()

