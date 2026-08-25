use std::net::TcpStream;
use std::sync::Mutex;
use std::time::{Duration, Instant};

use tauri::{Manager, State};
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

struct ServerState {
    port: u16,
    child: Mutex<Option<CommandChild>>,
}

#[tauri::command]
fn get_server_port(state: State<ServerState>) -> u16 {
    state.port
}

fn wait_for_port(port: u16, timeout: Duration) -> bool {
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        if TcpStream::connect(("127.0.0.1", port)).is_ok() {
            return true;
        }
        std::thread::sleep(Duration::from_millis(200));
    }
    false
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            let port = portpicker::pick_unused_port().expect("no hay puertos libres");
            // ponytail: en dev, la raíz del repo es el cwd del proceso Tauri
            // (src-tauri/../). El bundle instalado (con modelos GGUF
            // distribuidos aparte) es un problema de packaging separado,
            // fuera del alcance del MVP CPU-only actual.
            let project_root = std::env::current_dir()
                .expect("no se pudo resolver el cwd")
                .parent()
                .expect("src-tauri debería tener un padre")
                .to_path_buf();
            let (_rx, child) = app
                .shell()
                .sidecar("llm-lab-server")
                .expect("no se encontró el sidecar llm-lab-server")
                .env("LLM_LAB_SERVER_PORT", port.to_string())
                .env(
                    "LLM_LAB_PROJECT_ROOT",
                    project_root.to_string_lossy().to_string(),
                )
                .spawn()
                .expect("no se pudo lanzar el sidecar llm-lab-server");

            // ponytail: healthcheck simple por TCP connect, no HTTP real —
            // alcanza para saber que daphne ya está escuchando en el puerto.
            if !wait_for_port(port, Duration::from_secs(30)) {
                log::error!("el sidecar no respondió en el puerto {port} tras 30s");
            }

            app.manage(ServerState {
                port,
                child: Mutex::new(Some(child)),
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![get_server_port])
        .on_window_event(|window, event| {
            if matches!(
                event,
                tauri::WindowEvent::CloseRequested { .. } | tauri::WindowEvent::Destroyed
            ) {
                let state = window.state::<ServerState>();
                let child = state.child.lock().unwrap().take();
                if let Some(child) = child {
                    let _ = child.kill();
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
