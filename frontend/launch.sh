
#!/usr/bin/env zsh

# 阻塞式启动脚本：
#!/usr/bin/env zsh

# 阻塞式启动脚本：
# 1) 在后端根目录启动后端 launch.sh（优先使用指定 conda env 的 python）
# 2) 等待后端监听端口可用
# 3) 启动前端 pnpm dev
# 4) 阻塞并监控两个进程；在收到 SIGINT/SIGTERM 或任一进程退出时，自动停止并清理两者

set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "$0")/.." && pwd)/backend"
BACKEND_LAUNCH="$BACKEND_DIR/launch.sh"
BACKEND_LOG="$BACKEND_DIR/backend.log"

# 从项目常量里知道后端监听地址（默认见 src/constant/strings.tsx）
BACKEND_HOST="localhost"
BACKEND_PORT=8000

# 指定 conda python 路径（由你提供）
CONDA_PYTHON="/Users/evan/miniconda3/envs/django_hw/bin/python"

if [ ! -f "$BACKEND_LAUNCH" ]; then
	echo "Cannot find backend launch script: $BACKEND_LAUNCH"
	exit 1
fi

if [ ! -x "$BACKEND_LAUNCH" ]; then
	echo "Making backend launch script executable: $BACKEND_LAUNCH"
	chmod +x "$BACKEND_LAUNCH" || true
fi

# 启动后端（在后端根目录运行）, 输出写入后端日志
if [ -x "$CONDA_PYTHON" ]; then
	CONDA_BIN_DIR="$(dirname "$CONDA_PYTHON")"
	echo "Starting backend with conda python at $CONDA_PYTHON"
	# use exec to replace the shell so $! refers to the actual backend process
	bash -lc "cd '$BACKEND_DIR' && exec env PATH='$CONDA_BIN_DIR:$PATH' '$BACKEND_LAUNCH'" > "$BACKEND_LOG" 2>&1 &
else
	echo "Conda python not found at $CONDA_PYTHON. Starting backend with current PATH." >&2
	bash -lc "cd '$BACKEND_DIR' && exec '$BACKEND_LAUNCH'" > "$BACKEND_LOG" 2>&1 &
fi

BACKEND_PID=$!
echo "Backend started (pid=$BACKEND_PID), logging to $BACKEND_LOG"

# 等待后端端口可用
echo "Waiting for backend at ${BACKEND_HOST}:${BACKEND_PORT} to be ready..."
MAX_WAIT=30
SLEEP_INTERVAL=1
elapsed=0
while [ $elapsed -lt $MAX_WAIT ]; do
	if command -v curl >/dev/null 2>&1; then
		if curl -s "http://${BACKEND_HOST}:${BACKEND_PORT}/" >/dev/null 2>&1; then
			echo "Backend responded on http://${BACKEND_HOST}:${BACKEND_PORT}"
			break
		fi
	elif command -v nc >/dev/null 2>&1; then
		if nc -z "$BACKEND_HOST" "$BACKEND_PORT" >/dev/null 2>&1; then
			echo "Backend port ${BACKEND_PORT} is open"
			break
		fi
	else
		if grep -E "listening|started|running|ready|${BACKEND_PORT}" "$BACKEND_LOG" >/dev/null 2>&1; then
			echo "Detected backend ready message in log"
			break
		fi
	fi

	sleep $SLEEP_INTERVAL
	elapsed=$((elapsed + SLEEP_INTERVAL))
	echo "... waited ${elapsed}s"
done

if [ $elapsed -ge $MAX_WAIT ]; then
	echo "Warning: Backend did not become ready within ${MAX_WAIT}s. Check $BACKEND_LOG for details."
fi

# Try to detect the actual process listening on the backend port. Some backend launch
# scripts daemonize or spawn a child and exit, so $! might not be the real server PID.
BACKEND_PGID=""
if command -v lsof >/dev/null 2>&1; then
	LISTENER_PID=$(lsof -ti TCP:"$BACKEND_PORT" | head -n 1 || true)
elif command -v ss >/dev/null 2>&1; then
	LISTENER_PID=$(ss -ltnp 2>/dev/null | awk -v p="$BACKEND_PORT" '$4 ~ (":"p"$|:"p"->) { if ($6 ~ /pid=/) { sub(/.*pid=/,"",$6); sub(/,.*$/,"",$6); print $6; exit } }')
else
	LISTENER_PID=""
fi

if [ -n "${LISTENER_PID:-}" ]; then
	echo "Detected backend listening PID: $LISTENER_PID (using this PID for cleanup)"
	BACKEND_PID=$LISTENER_PID
	# try to get process group id for more reliable killing
	if command -v ps >/dev/null 2>&1; then
		BACKEND_PGID=$(ps -o pgid= $BACKEND_PID 2>/dev/null | tr -d ' ' || true)
		if [ -n "${BACKEND_PGID:-}" ]; then
			echo "Backend process group id: $BACKEND_PGID"
		fi
	fi
fi

# 启动前端并记录 PID
echo "Starting frontend (pnpm dev)"
pnpm dev > ./frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend started (pid=$FRONTEND_PID), logging to ./frontend.log"

# 清理函数
cleanup() {
	echo "Stopping servers..."
	if [ -n "${FRONTEND_PID:-}" ]; then
		if kill -0 $FRONTEND_PID >/dev/null 2>&1; then
			echo "Killing frontend (pid=$FRONTEND_PID)"
			kill $FRONTEND_PID >/dev/null 2>&1 || true
		fi
	fi
	if [ -n "${BACKEND_PGID:-}" ]; then
		echo "Killing backend process group (pgid=$BACKEND_PGID)"
		kill -TERM -"$BACKEND_PGID" >/dev/null 2>&1 || true
		sleep 1
		kill -KILL -"$BACKEND_PGID" >/dev/null 2>&1 || true
	elif [ -n "${BACKEND_PID:-}" ]; then
		if kill -0 $BACKEND_PID >/dev/null 2>&1; then
			echo "Killing backend (pid=$BACKEND_PID)"
			kill $BACKEND_PID >/dev/null 2>&1 || true
			# give it a moment
			sleep 1
		fi
		# If backend process spawned children (daemonized), also find and kill descendants
		# Collect descendants using ps (works on macOS/Linux)
		if command -v ps >/dev/null 2>&1; then
			echo "Looking for backend descendant processes to kill..."
			# build a list of descendants via BFS
			descendants=()
			queue=("$BACKEND_PID")
			while [ ${#queue[@]} -gt 0 ]; do
				parent=${queue[0]}
				queue=(${queue[@]:1})
				# find direct children of parent
				for child in $(ps -eo pid,ppid | awk -v p=$parent '$2==p {print $1}'); do
					# avoid duplicates
					if [[ ! " ${descendants[@]} " =~ " ${child} " ]]; then
						descendants+=($child)
						queue+=($child)
					fi
				done
			done
			if [ ${#descendants[@]} -gt 0 ]; then
				echo "Found descendant PIDs: ${descendants[*]}"
				for dp in ${descendants[@]}; do
					if kill -0 $dp >/dev/null 2>&1; then
						echo "Killing descendant pid $dp"
						kill $dp >/dev/null 2>&1 || true
					fi
				done
				sleep 1
			fi
		fi
		# if still alive, try killing the process group (negative PID) as last resort
		if kill -0 $BACKEND_PID >/dev/null 2>&1; then
			echo "Backend still alive; killing process group (-$BACKEND_PID)"
			kill -TERM -$BACKEND_PID >/dev/null 2>&1 || true
			sleep 1
			kill -KILL -$BACKEND_PID >/dev/null 2>&1 || true
		fi
	fi
	# give processes a moment to exit
	sleep 1
}

trap 'cleanup; exit 0' INT TERM EXIT

echo "\nFront end on http://localhost:3000\n"

# 监控两个进程
echo "Blocking: monitoring backend (pid=$BACKEND_PID) and frontend (pid=$FRONTEND_PID). Press Ctrl-C to stop both."
while true; do
	sleep 1
	alive_backend=0
	alive_frontend=0
	if [ -n "${BACKEND_PID:-}" ] && kill -0 $BACKEND_PID >/dev/null 2>&1; then
		alive_backend=1
	fi
	if [ -n "${FRONTEND_PID:-}" ] && kill -0 $FRONTEND_PID >/dev/null 2>&1; then
		alive_frontend=1
	fi

	if [ $alive_backend -eq 0 ] || [ $alive_frontend -eq 0 ]; then
		echo "One or both processes exited (backend_alive=$alive_backend, frontend_alive=$alive_frontend). Exiting and cleaning up..."
		break
	fi
done

# 调用 cleanup（trap 也会触发）
cleanup

echo "Done. Backend pid=$BACKEND_PID, Frontend pid=$FRONTEND_PID"

echo "To follow logs in another terminal:"
echo "  tail -f $BACKEND_LOG ./frontend.log"

exit 0
						kill -TERM -"$BACKEND_PGID" >/dev/null 2>&1 || true
						sleep 1
						kill -KILL -"$BACKEND_PGID" >/dev/null 2>&1 || true
					elif [ -n "${BACKEND_PID:-}" ]; then
						if kill -0 $BACKEND_PID >/dev/null 2>&1; then
							echo "Killing backend (pid=$BACKEND_PID)"
							kill $BACKEND_PID >/dev/null 2>&1 || true
							# give it a moment
							sleep 1
						fi
						# If backend process spawned children (daemonized), also find and kill descendants
					# Collect descendants using ps (works on macOS/Linux)
					if command -v ps >/dev/null 2>&1; then
						echo "Looking for backend descendant processes to kill..."
						# build a list of descendants via BFS
						descendants=()
						queue=("$BACKEND_PID")
						while [ ${#queue[@]} -gt 0 ]; do
							parent=${queue[0]}
							queue=(${queue[@]:1})
							# find direct children of parent
							for child in $(ps -eo pid,ppid | awk -v p=$parent '$2==p {print $1}'); do
								# avoid duplicates
								if [[ ! " ${descendants[@]} " =~ " ${child} " ]]; then
									descendants+=($child)
									queue+=($child)
								fi
							done
						done
						if [ ${#descendants[@]} -gt 0 ]; then
							echo "Found descendant PIDs: ${descendants[*]}"
							for dp in ${descendants[@]}; do
								if kill -0 $dp >/dev/null 2>&1; then
									echo "Killing descendant pid $dp"
									kill $dp >/dev/null 2>&1 || true
								fi
							done
							sleep 1
						fi
					fi
					# if still alive, try killing the process group (negative PID) as last resort
					if kill -0 $BACKEND_PID >/dev/null 2>&1; then
						echo "Backend still alive; killing process group (-$BACKEND_PID)"
						kill -TERM -$BACKEND_PID >/dev/null 2>&1 || true
						sleep 1
						kill -KILL -$BACKEND_PID >/dev/null 2>&1 || true
					fi
				fi
				# give processes a moment to exit
				sleep 1
			}

			trap 'cleanup; exit 0' INT TERM EXIT

			echo "\nFront end on http://localhost:3000\n"

			# 监控两个进程
			echo "Blocking: monitoring backend (pid=$BACKEND_PID) and frontend (pid=$FRONTEND_PID). Press Ctrl-C to stop both."
			while true; do
				sleep 1
				alive_backend=0
				alive_frontend=0
				if [ -n "${BACKEND_PID:-}" ] && kill -0 $BACKEND_PID >/dev/null 2>&1; then
					alive_backend=1
				fi
				if [ -n "${FRONTEND_PID:-}" ] && kill -0 $FRONTEND_PID >/dev/null 2>&1; then
					alive_frontend=1
				fi

				if [ $alive_backend -eq 0 ] || [ $alive_frontend -eq 0 ]; then
					echo "One or both processes exited (backend_alive=$alive_backend, frontend_alive=$alive_frontend). Exiting and cleaning up..."
					break
				fi
			done

			# 调用 cleanup（trap 也会触发）
			cleanup

			echo "Done. Backend pid=$BACKEND_PID, Frontend pid=$FRONTEND_PID"

			echo "To follow logs in another terminal:"
			echo "  tail -f $BACKEND_LOG ./frontend.log"

			exit 0
		fi
	done

	# 调用 cleanup（trap 也会触发）
	cleanup

	echo "Done. Backend pid=$BACKEND_PID, Frontend pid=$FRONTEND_PID"

	echo "To follow logs in another terminal:"
	echo "  tail -f $BACKEND_LOG ./frontend.log"

	exit 0
