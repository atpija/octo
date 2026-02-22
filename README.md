<div align="center">
  <img src="octo_logo.png" alt="Octo Logo" width="200">
</div>

# Octo - Remote Code Execution Platform

[![License](https://img.shields.io/badge/license-MIT%2FApache--2.0-green.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-yellow.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-required-blue.svg)](https://www.docker.com/)

Octo is a distributed remote code execution platform that enables seamless execution of code in isolated, containerized environments. Execute code on remote servers with easy-to-use CLI commands.

More Information: https://www.project-octo.com/

## Key Features

- **Multi-Language Support**: Python, JavaScript, Go, Rust, Ruby, and more
- **Client-Server Architecture**: Distributed execution with token-based authentication
- **Docker Integration**: Automatic containerization for each execution
- **Resource Management**: Control CPU, RAM, GPU, and shared memory allocation
- **Real-time Output Streaming**: Monitor execution as it happens
- **Simple CLI**: Easy-to-use command-line interface

## Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
  - [Client Commands](#client-commands)
  - [Server Commands](#server-commands)
  - [Runner Commands](#runner-commands)
- [Configuration](#configuration)
- [License](#license)

## Quick Start

### Prerequisites
- Python 3.11 or higher
- Docker
- pip package manager

### Installation
```bash
# Clone the repository
git clone https://github.com/atpija/octo

### Getting Started
# Build each Component

cd client
chmod +x build_installer.sh (Linux)
./build_installer.sh (Linux) | ./build_installer.ps1 (Windows)

cd server
chmod +x build_installer.sh (Linux)
./build_installer.sh (Linux) | ./build_installer.ps1 (Windows)

cd runner
chmod +x build_installer.sh (Linux)
./build_installer.sh (Linux) | ./build_installer.ps1 (Windows)

# Install each Component
sudo dpkg -i octo-xy.deb (Linux)

Run the setup.exe for each Component (Windows)
```

### Basic Usage
You can run Octo local also for test purpose, start server and runner in a seperate Terminal/Powershell window.
```bash
# First add a token
octo-server token-add token123
# Run the Server
octo-server server

# Start the Runner in a seperate Terminal/Powershell
octo-runner --token token123

# Login to server
octo login --token token123 --server http://ip:port

# Run entry file
octo run main.py

# View and configure settings
octo config --help
```

## Architecture

Octo consists of three main components:

```
┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│   Client     │───────▶│    Server    │───────▶│    Runner    │
│ (Submitter)  │        │   (Queue)    │        │  (Executor)  │
└──────────────┘        └──────────────┘        └──────────────┘
```

- **Client**: Submits jobs from local machine
- **Server**: Manages task queue and credentials
- **Runner**: Executes tasks in Docker containers

## Usage

### Client Commands

| Command | Description |
|---------|-------------|
| `octo login --token token123 --server http://ip:port` | Login to server |
| `octo run main.py` | Run entry file in project folder |
| `octo config --help` | Show config help |
| `octo config --docker python:3.11` | Set Docker image |
| `octo config --install` | Install requirements.txt |
| `octo config --noinstall` | Skip requirements.txt installation |
| `octo config --gpu all` | Set GPU usage (e.g. none, all, 0, 0,1) |
| `octo config --ram 8g` | Set RAM limit |
| `octo config --cpu 2` | Set CPU limit |
| `octo config --shm-size 1g` | Set shared memory size |

**Examples:**

```bash
# Login
octo login --token demo-token --server http://192.168.1.100:5000

# Run a Python script
octo run script.py

# Configure for compute-intensive task
octo config --docker python:3.11
octo config --gpu all
octo config --ram 16g
octo config --cpu 8

# Run the task
octo run compute_task.py
```

### Server Commands

| Command | Description |
|---------|-------------|
| `octo-server server` | Start server |
| `octo-server token-list` | List tokens |
| `octo-server token-add demo-token` | Add a new token |
| `octo-server token-remove demo-token` | Remove a token |
| `octo-server server --host 0.0.0.0 --port 5001` | Start server with custom host and port |

**Examples:**

```bash
# Start server
octo-server server

# Start on custom port
octo-server server --host 0.0.0.0 --port 5001

# Manage tokens
octo-server token-add user1-token
octo-server token-list
octo-server token-remove user1-token
```

### Runner Commands

| Command | Description |
|---------|-------------|
| `octo-runner --token demo` | Start runner with token |
| `octo-runner --token demo --server http://ip:5001` | Start runner with custom server host |

**Examples:**

```bash
# Start runner (connects to default server)
octo-runner --token demo-token

# Start runner connecting to custom server
octo-runner --token demo-token --server http://192.168.1.100:5001

# Multiple runners for parallel execution each runner in its own Terminal/Powershell
octo-runner --token runner1 --server http://server:5000 
octo-runner --token runner2 --server http://server:5000 
octo-runner --token runner3 --server http://server:5000 
```

## Configuration

Configuration is stored in `~/.remotecompute/config.json`:

```json
{
  "server": "http://192.168.1.100:5000",
  "token": "demo-token",
  "docker_image": "python:3.11",
  "install": true,
  "gpu": "all",
  "ram": "8g",
  "cpu": 4,
  "shm_size": "1g"
}
```

### Supported Docker Images

The runner automatically selects Docker images based on file type:

| Extension | Default Image | Package Manager |
|-----------|---------------|-----------------|
| `.py` | `python:3.11` | pip |
| `.js` | `node:latest` | npm |
| `.go` | `golang:latest` | go mod |
| `.rs` | `rust:latest` | cargo |
| `.rb` | `ruby:latest` | bundle |

Override with: `octo config --docker IMAGE_NAME`

## Project Structure

```
octo/
├── client/      # CLI client
├── server/      # Task queue server
├── runner/      # Task executor
├── test/        # Tests
└── scripts/     # Utilities
```

## License

Octo is licensed under either of

    Apache License, Version 2.0, (LICENSE-APACHE or https://www.apache.org/licenses/LICENSE-2.0)
    MIT license (LICENSE-MIT or https://opensource.org/licenses/MIT)

at your option.

Unless you explicitly state otherwise, any contribution intentionally submitted for inclusion in Octo by you, as defined in the Apache-2.0 license, shall be dually licensed as above, without any additional terms or conditions.

## Contact

- **Project Lead**: Jan Pirringer
- **Email**: help@project-octo.com
- **Website**: https://www.project-octo.com/

---

**Made with ❤️ for the developer community**