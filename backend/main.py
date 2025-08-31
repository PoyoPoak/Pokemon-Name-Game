

@bot.event
async def on_message(message):
    # First check to avoid processing the bot's own messages
    if message.author == bot.user:
        return

    # Important: Process commands first to make sure they work correctly
    # This needs to happen before other message processing
    await bot.process_commands(message)
    
    try:
        # Check if message is part of an active game
        channel_id = message.channel.id
        if channel_id in active_games and active_games[channel_id]["is_running"]:
            # Skip command messages for game processing
            if message.content.startswith(bot.command_prefix):
                return
                
            game_data = active_games[channel_id]
            
            # Clean and check the message
            guess = clean_pokemon_name(message.content)
            if not guess:  # Skip empty guesses
                return
                
            print(f"Received guess: '{guess}' from {message.author.name}")
            
            # Optimized guess handling
            # Duplicate guess?
            if guess in game_data.get("guessed_clean", set()):
                print(f"Duplicate guess '{guess}' from {message.author.name}")
                await react_then_delete(message, '✅')
                return

            # Lookup cleaned guess
            positions = game_data.get("clean_to_positions", {}).get(guess)
            target_pos = None
            if positions:
                for p in positions:
                    if p in game_data["remaining_pokemon"]:
                        target_pos = p
                        break
            if target_pos is not None:
                name = game_data["remaining_pokemon"][target_pos]
                print(f"Match found! {guess} = {name}")
                game_data["guessed"][target_pos] = name
                game_data.setdefault("guessed_clean", set()).add(guess)
                del game_data["remaining_pokemon"][target_pos]
                # Update header & section
                time_left = game_data["end_time"] - time.time()
                time_str = format_time(time_left)
                total_guessed = len(game_data["guessed"])
                header = generate_grid_header(total_guessed, time_str)
                await game_data["header_message"].edit(content=f"```\n{header}\n```")
                pokemon_per_section = (151 + GRID_SECTIONS - 1) // GRID_SECTIONS
                section_index = (target_pos - 1) // pokemon_per_section
                if section_index < len(game_data["grid_messages"]):
                    grid_sections = generate_grid_sections(game_data["guessed"])
                    try:
                        await game_data["grid_messages"][section_index].edit(content=f"```\n{grid_sections[section_index]}\n```")
                    except discord.HTTPException as e:
                        print(f"Error updating grid section {section_index+1}: {e}")
                        simplified = "Grid segment - Contains guessed Pokémon"
                        await game_data["grid_messages"][section_index].edit(content=f"```\n{simplified}\n```")
                try:
                    await message.delete()
                except Exception as e:
                    print(f"Could not delete message: {e}")
                if len(game_data["guessed"]) == 151:
                    await message.channel.send("Congratulations! You've named all 151 original Pokémon!")
                    await end_game(message.channel)
            else:
                print(f"Incorrect guess: '{guess}' from {message.author.name}")
                await react_then_delete(message, '❌')
        
        if "shit" in message.content.lower():
            await message.delete()
            await message.channel.send(f"{message.author.mention} - dont use that word!")
    except Exception as e:
        print(f"Error in on_message: {type(e).__name__}: {str(e)}")


# Helper function to clean text
def clean_pokemon_name(name):
    # Only log this for messages with less than 50 characters to avoid console spam
    if len(name) < 50:
        cleaned = re.sub(r'[^a-zA-Z]', '', name).lower()
        print(f"Cleaned name: '{name}' -> '{cleaned}'")
        return cleaned
    else:
        # For longer content (like the grid itself), don't log
        return re.sub(r'[^a-zA-Z]', '', name).lower()

# Generate the game grid header (count and time)
def generate_grid_header(total_guessed, time_remaining_str):
    return f"{total_guessed}/151  |  {time_remaining_str}\n{'='*50}"

# Generate the game grid, split into sections
def generate_grid_sections(guessed_pokemon, sections=GRID_SECTIONS):
    # Calculate how many Pokémon to include per section
    pokemon_per_section = (151 + sections - 1) // sections  # Ceiling division
    grid_sections = []
    
    # Generate each section of the grid
    for section in range(sections):
        grid_lines = []
        start_pos = section * pokemon_per_section + 1
        end_pos = min((section + 1) * pokemon_per_section, 151)
        
        # Create a grid with 5 columns for this section
        items_in_section = end_pos - start_pos + 1
        rows_in_section = (items_in_section + 4) // 5  # Ceiling division for 5 columns
        
        for row in range(rows_in_section):
            line_items = []
            for col in range(5):
                pos = start_pos + row + col * rows_in_section
                if pos <= end_pos:
                    if pos in guessed_pokemon:
                        # Shorter format for guessed Pokémon
                        pokemon_name = guessed_pokemon[pos]
                        # Truncate long names to keep the grid compact
                        if len(pokemon_name) > 9:
                            pokemon_name = pokemon_name[:9]
                        line_items.append(f"{pos:3d}.{pokemon_name}")
                    else:
                        line_items.append(f"{pos:3d}.")
            
            # Pad each item to make columns align
            padded_items = [item.ljust(14) for item in line_items]
            grid_line = "".join(padded_items)
            
            # Only add non-empty lines
            if grid_line.strip():
                grid_lines.append(grid_line)
        
        grid_sections.append("\n".join(grid_lines))
    
    return grid_sections

# Generate the game grid (legacy method for compatibility)
def generate_grid(guessed_pokemon, time_remaining_str, total_guessed):
    header = generate_grid_header(total_guessed, time_remaining_str)
    sections = generate_grid_sections(guessed_pokemon)
    
    # Combine all sections into one grid for backward compatibility
    result = header + "\n" + "\n".join(sections)
    
    # Ensure the result is within Discord's message limit
    if len(result) > 1900:  # Leave some buffer for the code block markers
        return "Grid too large for display. Please use the multi-message grid format."
    
    return result

# Generate the final grid header
def generate_final_grid_header(total_guessed):
    return f"{total_guessed}/151  |  Time's up!\n{'='*50}"

# Generate the final grid sections with missed Pokemon
def generate_final_grid_sections(guessed_pokemon, missed_pokemon, sections=GRID_SECTIONS):
    # Calculate how many Pokémon to include per section
    pokemon_per_section = (151 + sections - 1) // sections  # Ceiling division
    grid_sections = []
    
    # Generate each section of the grid
    for section in range(sections):
        grid_lines = []
        start_pos = section * pokemon_per_section + 1
        end_pos = min((section + 1) * pokemon_per_section, 151)
        
        # Create a grid with 5 columns for this section
        items_in_section = end_pos - start_pos + 1
        rows_in_section = (items_in_section + 4) // 5  # Ceiling division for 5 columns
        
        for row in range(rows_in_section):
            line_items = []
            for col in range(5):
                pos = start_pos + row + col * rows_in_section
                if pos <= end_pos:
                    if pos in guessed_pokemon:
                        # Truncate long names to keep the grid compact
                        pokemon_name = guessed_pokemon[pos]
                        if len(pokemon_name) > 9:
                            pokemon_name = pokemon_name[:9]
                        line_items.append(f"{pos:3d}.{pokemon_name}")
                    else:
                        # For missed Pokémon, mark with a star (*) and show the name
                        pokemon_name = missed_pokemon[pos]
                        if len(pokemon_name) > 9:
                            pokemon_name = pokemon_name[:9]
                        line_items.append(f"*{pos:2d}.{pokemon_name}")
            
            # Pad each item to make columns align
            padded_items = [item.ljust(14) for item in line_items]
            grid_line = "".join(padded_items)
            
            # Only add non-empty lines
            if grid_line.strip():
                grid_lines.append(grid_line)
        
        grid_sections.append("\n".join(grid_lines))
    
    return grid_sections

# Display the final grid with missed Pokemon (legacy method for compatibility)
def generate_final_grid(guessed_pokemon, missed_pokemon):
    header = generate_final_grid_header(len(guessed_pokemon))
    sections = generate_final_grid_sections(guessed_pokemon, missed_pokemon)
    
    # Combine all sections into one grid for backward compatibility
    result = header + "\n" + "\n".join(sections)
    
    # If the result is still too long, show a summary instead
    if len(result) > 1900:
        found_count = len(guessed_pokemon)
        missed_count = 151 - found_count
        summary = [
            f"{found_count}/151  |  Time's up!",
            f"="*50,
            f"You found {found_count} Pokémon and missed {missed_count}.",
            f"Note: Missed Pokémon are marked with a star (*)",
            f"Examples: {', '.join(['*' + str(list(missed_pokemon.keys())[i]) + '. ' + list(missed_pokemon.values())[i] for i in range(min(5, missed_count))])}"
        ]
        return "\n".join(summary)
    
    return result

@bot.command()
async def play(ctx):
    try:
        print(f"Play command invoked by {ctx.author.name} in channel {ctx.channel.name}")
        channel = ctx.channel
        
        # Check if there's already a game running in this channel
        if channel.id in active_games:
            await ctx.send("A game is already in progress in this channel!")
            return
            
        # Initialize game state
        remaining_pokemon = {i+1: name for i, name in enumerate(ORIGINAL_POKEMON)}
        clean_to_positions = defaultdict(list)
        for pos, name in remaining_pokemon.items():
            clean_to_positions[clean_pokemon_name(name)].append(pos)
        game_data = {
            "guessed": {},
            "guessed_clean": set(),
            "remaining_pokemon": remaining_pokemon,
            "clean_to_positions": clean_to_positions,
            "header_message": None,
            "grid_messages": [],
            "is_running": True,
            "start_time": time.time(),
            "end_time": time.time() + 15 * 60,  # 15 minutes
        }
        active_games[channel.id] = game_data
        
        print("Sending initial messages...")
        
        # First message: header with count and time
        header = generate_grid_header(0, "15:00")
        game_data["header_message"] = await ctx.send(f"```\n{header}\n```")
        print(f"Header message sent with ID: {game_data['header_message'].id}")
        
        # Send each grid section as a separate message
        grid_sections = generate_grid_sections({})  # Empty grid to start
        
        for i, section in enumerate(grid_sections):
            try:
                msg = await ctx.send(f"```\n{section}\n```")
                game_data["grid_messages"].append(msg)
                print(f"Grid section {i+1} sent with ID: {msg.id}")
            except discord.HTTPException as e:
                print(f"Error sending grid section {i+1}: {str(e)}")
                # If there's an error, try sending a simplified version
                simplified = f"Grid segment - No Pokémon guessed yet"
                msg = await ctx.send(f"```\n{simplified}\n```")
                game_data["grid_messages"].append(msg)
        
        # Start the game loop
        print("Starting game loop...")
        game_task = asyncio.create_task(game_loop(channel))
        
        # Store the task so it doesn't get garbage collected
        game_data["task"] = game_task
        
        await ctx.send("Pokémon Quiz Game has started! You have 15 minutes to name all 151 original Pokémon!")
        print("Play command completed successfully")
    except Exception as e:
        print(f"Error in play command: {type(e).__name__}: {str(e)}")
        await ctx.send(f"An error occurred while starting the game: {type(e).__name__}")
        if channel.id in active_games:
            del active_games[channel.id]
