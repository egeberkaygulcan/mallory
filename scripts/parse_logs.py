import os
import argparse
import json
from datetime import datetime

def parse_event_text(event_text):
    """
    Parses the event text in the format "EventName(params);additional_params"
    Returns a dict with at least 'event_name', 'params', and 'additional_params'.
    You can extend this function to handle specific EventNames differently.
    """
    result = {
        'event_name': None,
        'params': None,
        'additional_params': None
    }
    if ';' in event_text:
        main_part, additional_params = event_text.split(';', 1)
        result['additional_params'] = additional_params.strip()
    else:
        main_part = event_text
    if '(' in main_part and ')' in main_part:
        event_name, params = main_part.split('(', 1)
        params = params.rstrip(')')
        result['event_name'] = event_name.strip()
        result['params'] = params.strip()
    else:
        result['event_name'] = main_part.strip()
    # You can add more parsing logic here based on event_name

    if result['event_name'] == "ClientRequest":
        params_parts = result['params'].split(',')
        if len(params_parts) >= 2:
            result['params'] = {
                'node_id': params_parts[0].strip(),
                'command': truncate_command(params_parts[1].strip())
            }
    elif result["event_name"] == "MembershipChange":
        params_parts = result['params'].split(',')
        if len(params_parts) >= 2:
            result['params'] = {
                'node_id': params_parts[1].strip(),
                'change_type': params_parts[0].strip()
            }
    elif result["event_name"] == "BecomeLeader":
        params_parts = result['params'].split(',')
        if len(params_parts) >= 2:
            result['params'] = {
                'term': params_parts[1].strip(),
                'node_id': params_parts[0].strip()
            }
    elif result["event_name"] == "UpdateSnapshot":
        params_parts = result['params'].split(',')
        if len(params_parts) >= 2:
            result['params'] = {
                'node_id': params_parts[0].strip(),
                'snapshot_idx': params_parts[1].strip()
            }
    elif result["event_name"] == "Timeout":
        result['params'] = {
            "node_id": result['params'].strip()
        }
    elif result["event_name"] == "MessageSend" or result["event_name"] == "MessageReceive":
        params_parts = result['params'].split(',')
        if len(params_parts) >= 3:
            result['params'] = {
                'message_type': params_parts[0].strip(),
                'from_node': params_parts[1].strip(),
                'to_node': params_parts[2].strip(),
                "additional_params": map_message_params(params_parts[0].strip(), result['additional_params'])
            }

    return result

def truncate_command(command_str):
    index = command_str.find("AAAA")
    return command_str[:index] if index != -1 else command_str

def map_message_params(message_type, additional_params):
    additional_params = additional_params.strip("()")
    if message_type == "append_entries_req":
        additional_params = additional_params.split(',')
        if len(additional_params) == 4:
            return {
                'term': additional_params[0].strip(),
                'prev_log_idx': additional_params[1].strip(),
                'prev_log_term': additional_params[2].strip(),
                'leader_commit': additional_params[3].strip()
            }
        if len(additional_params) == 6:
            return {
                'term': additional_params[0].strip(),
                'prev_log_idx': additional_params[1].strip(),
                'prev_log_term': additional_params[2].strip(),
                'entry_term': additional_params[3].strip(),
                'entry': truncate_command(additional_params[5].strip()),
                'leader_commit': additional_params[4].strip()
            }
    elif message_type == "append_entries_resp":
        additional_params = additional_params.split(',')
        if len(additional_params) == 4:
            return {
                'term': additional_params[0].strip(),
                'success': additional_params[1].strip(),
                'current_idx': additional_params[2].strip(),
                'msg_id': additional_params[3].strip()
            }
    elif message_type == "request_vote_req":
        additional_params = additional_params.split(',')
        if len(additional_params) == 5:
            return {
                'pre_vote': additional_params[0].strip(),
                'term': additional_params[1].strip(),
                'candidate_id': additional_params[2].strip(),
                'last_log_idx': additional_params[3].strip(),
                'last_log_term': additional_params[4].strip()
            }
    elif message_type == "request_vote_resp":
        additional_params = additional_params.split(',')
        if len(additional_params) == 4:
            return {
                'term': additional_params[0].strip(),
                'pre_vote': additional_params[1].strip(),
                'request_term': additional_params[2].strip(),
                'vote_granted': additional_params[3].strip()
            }

def parse_log_file(file_path, node_name):
    events = []
    with open(file_path, 'r') as f:
        for line in f:
            if '*' not in line:
                continue
            before_star, after_star = line.split('*', 1)
            if 'Event:' not in after_star:
                continue
            timestamp = before_star.strip()
            event_text = after_star.split('Event:', 1)[1].strip()
            parsed_event = parse_event_text(event_text)
            events.append({
                'timestamp': timestamp,
                'event': event_text,
                'parsed_event': parsed_event,
                'node': node_name
            })
    return events

def parse_timestamp(ts):
    # Example: '793:M 01 Jul 2025 15:32:57.369'
    # We'll ignore the '793:M' part
    try:
        parts = ts.split(' ', 1)[1]
        return datetime.strptime(parts, "%d %b %Y %H:%M:%S.%f")
    except Exception:
        return None

def translate_to_int(val):
    try:
        return int(val)
    except ValueError as e:
        return int(float(val))

def map_old_to_new(old_events):
    new_data = []

    # We'll track client requests and messages to generate consistent IDs or indexes
    client_request_count = 0
    client_command_to_request_id = {}
    node_map = {}


    for e in old_events:
        event = e["parsed_event"]
        name = event["event_name"]
        node = int(e["node"])
        if name == "ClientRequest" or name == "MembershipChange" or name == "Timeout":
            node_id = event["params"]["node_id"]
            if node_id not in node_map:
                node_map[node_id] = node
        if name == "ClientRequest":
            command = event["params"]["command"]
            if command not in client_command_to_request_id:
                client_command_to_request_id[command] = client_request_count
                client_request_count+=1
        if name == "MessageSend":
            node_id = event["params"]["from_node"]
            if node_id not in node_map:
                node_map[node_id] = node

            if event["params"]["message_type"] == "append_entries_req" and "entry" in event["params"]["additional_params"]:
                command = event["params"]["additional_params"]["entry"]
                if command not in client_command_to_request_id:
                    client_command_to_request_id[command] = client_request_count
                    client_request_count+=1

        if name == "MessageReceive":
            node_id = event["params"]["to_node"]
            if node_id not in node_map:
                node_map[node_id] = node

    for entry in old_events:
        evt = entry["parsed_event"]
        name = evt["event_name"]
        params = evt["params"]
        node = int(entry["node"])
        new_entry = {"Name": "", "Params": {}, "Reset": False}

        if name == "MembershipChange":
            if params["node_id"] not in node_map:
                node_map[params["node_id"]] = node
            new_entry["Name"] = "MembershipChange"
            new_entry["Params"] = {
                "action": params["change_type"],
                "node": node_map[params["node_id"]]
            }

        elif name == "Timeout":
            if params["node_id"] not in node_map:
                node_map[params["node_id"]] = node
            new_entry["Name"] = "Timeout"
            new_entry["Params"] = {
                "node": node_map[params["node_id"]]
            }

        elif name == "BecomeLeader":
            new_entry["Name"] = "BecomeLeader"
            new_entry["Params"] = {
                "node": node,
                "term": translate_to_int(params["term"])
            }

        elif name == "ClientRequest":
            new_entry["Name"] = "ClientRequest"
            command = params["command"]
            if command not in client_command_to_request_id:
                client_command_to_request_id[command] = client_request_count
                client_request_count += 1
            new_entry["Params"] = {
                "leader": node,
                "request": client_command_to_request_id[command]
            }

        elif name == "MessageSend":
            new_entry["Name"] = "SendMessage"
            p = params
            msg_type = p["message_type"]
            if p["from_node"] not in node_map:
                node_map[p["from_node"]] = node

            if msg_type == "append_entries_req":
                entries = []
                entry_data = p["additional_params"].get("entry", "")
                if entry_data:
                    entry_data = client_command_to_request_id[entry_data]
                    entries.append({"Term": translate_to_int(p["additional_params"]["entry_term"]), "Data": str(entry_data)})
                new_entry["Params"] = {
                    "type": "MsgApp",
                    "from": node_map[p["from_node"]],
                    "to": node_map[p["to_node"]],
                    "term": translate_to_int(p["additional_params"]["term"]),
                    "log_term": translate_to_int(p["additional_params"]["prev_log_term"]),
                    "index": translate_to_int(p["additional_params"]["prev_log_idx"]),
                    "commit": translate_to_int(p["additional_params"]["leader_commit"]),
                    "entries": entries,
                    "reject": False
                }
            elif msg_type == "append_entries_resp":
                new_entry["Params"] = {
                    "type": "MsgAppResp",
                    "from": node_map[p["from_node"]],
                    "to": node_map[p["to_node"]],
                    "term": translate_to_int(p["additional_params"]["term"]),
                    "log_term": 0,
                    "index": translate_to_int(p["additional_params"]["current_idx"]),
                    "commit": 0,
                    "entries": [],
                    "reject": p["additional_params"]["success"] == "0"
                }
            elif msg_type == "request_vote_req":
                new_entry["Params"] = {
                    "type": "MsgVote",
                    "from": node_map[p["from_node"]],
                    "to": node_map[p["to_node"]],
                    "term": translate_to_int(p["additional_params"]["term"]),
                    "log_term": translate_to_int(p["additional_params"]["last_log_term"]),
                    "index": translate_to_int(p["additional_params"]["last_log_idx"])
                }
            elif msg_type == "request_vote_resp":
                new_entry["Params"] = {
                    "type": "MsgVoteResp",
                    "from": node_map[p["from_node"]],
                    "to": node_map[p["to_node"]],
                    "term": translate_to_int(p["additional_params"]["term"]),
                    "reject": p["additional_params"]["vote_granted"] == "0"
                }

        elif name == "MessageReceive":
            new_entry["Name"] = "DeliverMessage"
            p = params
            msg_type = p["message_type"]
            if msg_type == "append_entries_req":
                entries = []
                entry_data = p["additional_params"].get("entry", "")
                if entry_data:
                    entry_data = client_command_to_request_id[entry_data]
                    entries.append({"Term": translate_to_int(p["additional_params"]["entry_term"]), "Data": str(entry_data)})
                new_entry["Params"] = {
                    "type": "MsgApp",
                    "from": node_map[p["from_node"]],
                    "to": node_map[p["to_node"]],
                    "term": translate_to_int(p["additional_params"]["term"]),
                    "log_term": translate_to_int(p["additional_params"]["prev_log_term"]),
                    "index": translate_to_int(p["additional_params"]["prev_log_idx"]),
                    "commit": translate_to_int(p["additional_params"]["leader_commit"]),
                    "entries": entries,
                    "reject": False
                }
            elif msg_type == "append_entries_resp":
                new_entry["Params"] = {
                    "type": "MsgAppResp",
                    "from": node_map[p["from_node"]],
                    "to": node_map[p["to_node"]],
                    "term": translate_to_int(p["additional_params"]["term"]),
                    "log_term": 0,
                    "index": translate_to_int(p["additional_params"]["current_idx"]),
                    "commit": 0,
                    "entries": [],
                    "reject": p["additional_params"]["success"] == "0"
                }
            elif msg_type == "request_vote_req":
                new_entry["Params"] = {
                    "type": "MsgVote",
                    "from": node_map[p["from_node"]],
                    "to": node_map[p["to_node"]],
                    "term": translate_to_int(p["additional_params"]["term"]),
                    "log_term": translate_to_int(p["additional_params"]["last_log_term"]),
                    "index": translate_to_int(p["additional_params"]["last_log_idx"])
                }
            elif msg_type == "request_vote_resp":
                new_entry["Params"] = {
                    "type": "MsgVoteResp",
                    "from": node_map[p["from_node"]],
                    "to": node_map[p["to_node"]],
                    "term": translate_to_int(p["additional_params"]["term"]),
                    "reject": p["additional_params"]["vote_granted"] == "0"
                }

        else:
            continue  # skip unknown event types

        new_data.append(new_entry)
    return new_data

def find_highest_client_request(events):
    highest = 0
    for e in events:
        if e["Name"] == "ClientRequest":
            request_id = e["Params"]["request"]
            if request_id > highest:
                highest = request_id
    print(highest)

def main():
    parser = argparse.ArgumentParser(description='Parse and unify redis.log files.')
    parser.add_argument('directory', help='Directory containing n1, n2, n3 subdirectories')
    args = parser.parse_args()

    if not args.directory:
        print("Error: Directory argument is required.")
        return

    if not os.path.isdir(args.directory):
        print(f"Error: {args.directory} is not a directory.")
        return

    all_events = []

    for subdir in ['1', '2', '3']:
        log_path = os.path.join(args.directory, "n"+subdir, "opt", "redis-log", 'redis.log')
        if os.path.isfile(log_path):
            events = parse_log_file(log_path, subdir)
            all_events.extend(events)
        else:
            print(f"Warning: {log_path} not found.")

    # Sort all events by timestamp
    all_events = [
        e for e in all_events if parse_timestamp(e['timestamp']) is not None
    ]
    all_events.sort(key=lambda e: parse_timestamp(e['timestamp']))

    all_events = map_old_to_new(all_events)
    find_highest_client_request(all_events)

    # Write unified log file
    output_path = os.path.join(args.directory, 'unified_log.json')
    with open(output_path, 'w') as out_f:
        json.dump(all_events, out_f, indent=2)
    print(f"Unified log written to {output_path}")

if __name__ == "__main__":
    main()
