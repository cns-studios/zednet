"""
Main GUI application using Tkinter (cross-platform).
For production, consider migrating to PyQt5 for better UX.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from pathlib import Path
import threading
import logging
import asyncio
from typing import Optional, Callable
from queue import Queue
from .log_handler import QueueHandler
from .theme import Theme

logger = logging.getLogger(__name__)

class ZedNetGUI:
    """Main GUI application."""

    def __init__(self, app_controller):
        """
        Args:
            app_controller: Main application controller
        """
        self.controller = app_controller
        self.root = tk.Tk()
        self.root.title("ZedNet - Decentralized Web")
        self.root.geometry("1000x650")
        
        # Style
        self.style = ttk.Style()
        self._set_theme('light')
        
        # Create UI
        self._create_menu()
        self._create_main_content()
        self._create_status_bar()

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Set up logging
        self.log_queue = Queue()
        queue_handler = QueueHandler(self.log_queue)
        logging.getLogger().addHandler(queue_handler)

        # Start update loops
        self._process_log_queue()
        self._update_ui()
    
    def _create_menu(self):
        """Create menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Create Site...", command=self._create_site_dialog)
        file_menu.add_command(label="Import Site...", command=self._import_site_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_closing)
        
        # View menu (for theme switching)
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Light Mode", command=lambda: self._set_theme('light'))
        view_menu.add_command(label="Dark Mode", command=lambda: self._set_theme('dark'))

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
        help_menu.add_command(label="Terms of Service", command=self._show_terms)

    def _set_theme(self, mode: str):
        """Set the application theme."""
        self.current_theme = mode
        Theme.apply_theme(self.style, mode)

        # Update specific widget colors that don't auto-update
        log_bg = Theme.DARK_SURFACE if mode == 'dark' else Theme.LIGHT_SURFACE
        log_fg = Theme.DARK_TEXT if mode == 'dark' else Theme.LIGHT_TEXT
        if hasattr(self, 'log_text'):
            self.log_text.config(background=log_bg, foreground=log_fg)

    def _create_status_bar(self):
        """Create status bar."""
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)
        
        self.status_label_left = ttk.Label(self.status_frame, text="Welcome to ZedNet", style="Status.TLabel")
        self.status_label_left.pack(side=tk.LEFT, padx=5)

        self.status_label_right = ttk.Label(self.status_frame, text="Server: http://127.0.0.1:9999", style="Status.TLabel")
        self.status_label_right.pack(side=tk.RIGHT, padx=5)

    def _show_status_message(self, message: str, duration_ms: int = 4000):
        """Display a temporary message in the status bar."""
        self.status_label_left.config(text=message)
        self.root.after(duration_ms, lambda: self.status_label_left.config(text=""))

    def _create_main_content(self):
        """Create main content area."""
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Sites tab
        self.sites_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.sites_frame, text="My Sites")
        self._create_sites_tab()
        
        # Downloads tab
        self.downloads_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.downloads_frame, text="Downloaded Sites")
        self._create_downloads_tab()
        
        # Log tab
        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_frame, text="Logs")
        self._create_log_tab()
    
    def _create_sites_tab(self):
        """Create my sites tab."""
        # Sites list
        columns = ('Name', 'Site ID', 'Status', 'Peers', 'Upload')
        self.sites_tree = ttk.Treeview(
            self.sites_frame,
            columns=columns,
            show='headings'
        )
        
        for col in columns:
            self.sites_tree.heading(col, text=col)
        
        self.sites_tree.column('Name', width=200)
        self.sites_tree.column('Site ID', width=250)
        self.sites_tree.column('Status', width=100)
        self.sites_tree.column('Peers', width=80)
        self.sites_tree.column('Upload', width=120)

        self.sites_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(
            self.sites_frame,
            orient=tk.VERTICAL,
            command=self.sites_tree.yview
        )
        self.sites_tree.configure(yscrollcommand=scrollbar.set)
        # Place scrollbar inside the frame but pack it to the right
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.sites_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)


        # Right-click menu
        self.sites_menu = tk.Menu(self.sites_tree, tearoff=0)
        self.sites_menu.add_command(label="Publish Site", command=self._publish_site)
        self.sites_menu.add_command(label="Stop Seeding", command=self._stop_seeding)
        self.sites_menu.add_separator()
        self.sites_menu.add_command(label="Copy Site ID", command=self._copy_site_id)
        self.sites_menu.add_separator()
        self.sites_menu.add_command(label="Remove Site...", command=self._remove_site)

        self.sites_tree.bind("<Button-3>", self._show_sites_menu)
    
    def _create_downloads_tab(self):
        """Create downloads tab."""
        # Toolbar
        toolbar = ttk.Frame(self.downloads_frame)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Label(toolbar, text="Site ID:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.site_id_entry = ttk.Entry(toolbar)
        self.site_id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Button(
            toolbar,
            text="Add Site",
            command=self._add_site_from_entry
        ).pack(side=tk.LEFT, padx=5)
        
        # Downloads list
        columns = ('Site ID', 'Progress', 'Status', 'Down', 'Up', 'Peers')
        self.downloads_tree = ttk.Treeview(
            self.downloads_frame,
            columns=columns,
            show='headings'
        )
        
        for col in columns:
            self.downloads_tree.heading(col, text=col)

        self.downloads_tree.column('Site ID', width=250)
        self.downloads_tree.column('Progress', width=100)
        self.downloads_tree.column('Status', width=100)
        self.downloads_tree.column('Down', width=120)
        self.downloads_tree.column('Up', width=120)
        self.downloads_tree.column('Peers', width=80)
        
        self.downloads_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(
            self.downloads_frame,
            orient=tk.VERTICAL,
            command=self.downloads_tree.yview
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.downloads_tree.configure(yscrollcommand=scrollbar.set)
    
    def _create_log_tab(self):
        """Create log viewer tab."""
        self.log_text = scrolledtext.ScrolledText(
            self.log_frame,
            wrap=tk.WORD,
            font=('Courier', 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self._set_theme(self.current_theme) # Apply theme to log viewer
    
    def _create_site_dialog(self):
        """Show create site dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Create New Site")
        dialog.geometry("500x300")
        
        # Site name
        ttk.Label(dialog, text="Site Name:").pack(pady=5)
        name_entry = ttk.Entry(dialog, width=50)
        name_entry.pack(pady=5)
        
        # Content directory
        ttk.Label(dialog, text="Content Directory:").pack(pady=5)
        
        path_frame = ttk.Frame(dialog)
        path_frame.pack(pady=5)
        
        path_entry = ttk.Entry(path_frame, width=40)
        path_entry.pack(side=tk.LEFT, padx=5)
        
        def browse():
            folder = filedialog.askdirectory()
            if folder:
                path_entry.delete(0, tk.END)
                path_entry.insert(0, folder)
        
        ttk.Button(path_frame, text="Browse", command=browse).pack(side=tk.LEFT)
        
        # Password
        ttk.Label(dialog, text="Password (optional):").pack(pady=5)
        password_entry = ttk.Entry(dialog, width=50, show="*")
        password_entry.pack(pady=5)
        
        # Create button
        def create():
            site_name = name_entry.get().strip()
            content_path = path_entry.get().strip()
            password = password_entry.get().strip() or None
            
            if not site_name or not content_path:
                messagebox.showerror("Error", "Please fill all required fields")
                return

            create_button.config(state="disabled")

            def on_site_created(result):
                if result:
                    messagebox.showinfo(
                        "Success",
                        f"Site created!\n\nSite ID:\n{result['site_id']}\n\n"
                        f"Share this ID with others to let them access your site."
                    )
                    self._update_sites_list()
                    dialog.destroy()
                else:
                    # Re-enable button on failure
                    create_button.config(state="normal")
                    self._show_status_message("Error: Failed to create site.")
            
            coro = self.controller.create_site(
                site_name,
                Path(content_path),
                password
            )
            self._run_async(coro, on_site_created)

        create_button = ttk.Button(dialog, text="Create Site", command=create)
        create_button.pack(pady=20)

    def _on_closing(self):
        """Handle window closing."""
        logger.info("Closing GUI.")
        self.root.destroy()

    def _run_async(self, coro, callback: Optional[Callable] = None):
        """
        Run a coroutine on the controller's event loop.
        An optional callback can be executed with the result in the main thread.
        """
        async def coroutine_wrapper():
            try:
                result = await coro
                if callback:
                    self.root.after(0, callback, result)
            except Exception as e:
                logger.error(f"Async operation failed: {e}", exc_info=True)
                self.root.after(0, lambda e=e: self._show_status_message(f"Error: {e}"))

        self.controller.loop.call_soon_threadsafe(
            asyncio.create_task, coroutine_wrapper()
        )

    def _run_in_thread(self, target_func: Callable, callback: Optional[Callable] = None):
        """
        Run a synchronous (blocking) function in a separate thread.
        An optional callback can be executed with the result in the main thread.
        """
        def thread_target():
            try:
                result = target_func()
                if callback:
                    self.root.after(0, callback, result)
            except Exception as e:
                logger.error(f"Threaded operation failed: {e}", exc_info=True)
                self.root.after(0, lambda e=e: self._show_status_message(f"Error: {e}"))

        threading.Thread(target=thread_target, daemon=True).start()

    def _add_site_from_entry(self):
        """Add site from entry field."""
        site_id = self.site_id_entry.get().strip()
        if not site_id:
            messagebox.showerror("Error", "Please enter a Site ID")
            return
        
        self._show_status_message(f"Adding site: {site_id[:16]}...")

        def on_site_added(result):
            if result:
                self._show_status_message(f"Successfully added site: {site_id[:16]}")
            else:
                self._show_status_message(f"Failed to add site: {site_id[:16]}")

        self._run_async(self.controller.add_site(site_id), on_site_added)
        self.site_id_entry.delete(0, tk.END)
    
    def _open_site_in_browser(self):
        """Open selected site in browser."""
        selection = self.downloads_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a site")
            return
        
        item = self.downloads_tree.item(selection[0])
        site_id = item['values'][0]
        
        import webbrowser
        url = f"http://127.0.0.1:9999/site/{site_id}/index.html"
        webbrowser.open(url)
    
    def _publish_site(self):
        """Publish selected site."""
        selection = self.sites_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a site")
            return
        
        site_id = selection[0]

        password = self._ask_password()

        self._show_status_message(f"Publishing site: {site_id[:16]}...")

        def on_site_published(result):
            if result:
                self._show_status_message(f"Successfully published site: {site_id[:16]}")
            else:
                self._show_status_message(f"Failed to publish site: {site_id[:16]}")

        self._run_async(self.controller.publish_site(site_id, password), on_site_published)

    def _ask_password(self) -> Optional[str]:
        """Show a dialog to ask for a password."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Password Required")
        dialog.geometry("300x150")

        ttk.Label(dialog, text="Enter private key password (if any):").pack(pady=10)

        password_entry = ttk.Entry(dialog, show="*")
        password_entry.pack(pady=5)
        password_entry.focus_set()

        password = None
        def on_ok():
            nonlocal password
            password = password_entry.get()
            dialog.destroy()

        ttk.Button(dialog, text="OK", command=on_ok).pack(pady=10)

        dialog.transient(self.root)
        dialog.wait_window()

        return password
    
    def _stop_seeding(self):
        """Stop seeding selected site."""
        selection = self.sites_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a site")
            return
        
        # TODO: Implement stop seeding
        self._show_status_message("Stop seeding functionality not yet implemented.")

    def _show_sites_menu(self, event):
        """Show right-click menu for my sites."""
        selection = self.sites_tree.identify_row(event.y)
        if selection:
            self.sites_tree.selection_set(selection)
            self.sites_menu.post(event.x_root, event.y_root)

    def _copy_site_id(self):
        """Copy selected site ID to clipboard."""
        selection = self.sites_tree.selection()
        if not selection:
            return

        site_id = selection[0]
        self.root.clipboard_clear()
        self.root.clipboard_append(site_id)
        messagebox.showinfo("Copied", "Site ID copied to clipboard.")
    
    def _add_site_dialog(self):
        """Show add site dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Site")
        dialog.geometry("600x150")
        
        ttk.Label(dialog, text="ZedNet Site ID:").pack(pady=10)
        
        entry = ttk.Entry(dialog, width=70)
        entry.pack(pady=5)
        
        def add():
            site_id = entry.get().strip()
            if site_id:
                messagebox.showinfo("In Progress", f"Adding site: {site_id}...")

                def on_site_added(result):
                    if result:
                        logger.info(f"Successfully started download for site: {site_id}")
                    else:
                        messagebox.showerror("Error", f"Failed to add site: {site_id}")

                self._run_async(self.controller.add_site(site_id), on_site_added)
                dialog.destroy()
        
        ttk.Button(dialog, text="Add", command=add).pack(pady=10)
    
    def _remove_site(self):
        """Remove selected site from my sites."""
        selection = self.sites_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a site to remove.")
            return

        site_id = selection[0]

        # Confirmation dialog
        if not messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to permanently delete site {site_id[:16]}...?"
            "\nThis action cannot be undone."
        ):
            return

        # Ask about private key
        delete_key = messagebox.askyesno(
            "Delete Private Key?",
            "Do you also want to delete the private key for this site?"
            "\nWARNING: Without the key, you can never publish updates again."
            "\n(This is IRREVERSIBLE)"
        )

        self._show_status_message(f"Deleting site: {site_id[:16]}...")

        def on_site_deleted(success):
            if success:
                self._show_status_message("Site deleted successfully.")
                self._update_sites_list()  # Refresh the list
            else:
                self._show_status_message("Error: Failed to delete site.")

        # Run the blocking delete operation in a separate thread
        self._run_in_thread(
            lambda: self.controller.delete_my_site(site_id, delete_key),
            on_site_deleted
        )
    
    def _import_site_dialog(self):
        """Show import site dialog."""
        # TODO: Implement
        messagebox.showinfo("Info", "Not yet implemented")
    
    def _show_about(self):
        """Show about dialog."""
        messagebox.showinfo(
            "About ZedNet",
            "ZedNet v0.1.0-alpha\n\n"
            "Decentralized Web Platform\n\n"
            "Built with security and privacy in mind.\n\n"
            "Visit: github.com/yourname/zednet"
        )
    
    def _show_terms(self):
        """Show terms of service."""
        # TODO: Show full terms
        messagebox.showinfo(
            "Terms of Service",
            "Please read legal/TERMS_OF_SERVICE.md\n\n"
            "By using ZedNet, you agree to use it responsibly."
        )
    
    def _update_ui(self):
        """Update UI elements periodically."""
        try:
            # Update status bar indicators
            vpn_status = self.controller.get_vpn_status()
            vpn_text = "VPN: Active" if vpn_status['appears_safe'] else "VPN: WARNING"
            p2p_text = "P2P: Online" if self.controller.is_p2p_online() else "P2P: Offline"
            
            # Combine status and update right label
            self.status_label_right.config(text=f"{vpn_text}  |  {p2p_text}  |  Server: http://127.0.0.1:9999")
            
            # Update sites list
            self._update_sites_list()
            
            # Update downloads list
            self._update_downloads_list()
            
        except Exception as e:
            logger.error("UI update error: %s", e)
        
        # Schedule next update
        self.root.after(1000, self._update_ui)
    
    def _update_sites_list(self):
        """Update my sites list."""
        # Preserve selection
        selected_id = None
        if self.sites_tree.selection():
            selected_id = self.sites_tree.selection()[0]

        # Clear existing
        for item in self.sites_tree.get_children():
            self.sites_tree.delete(item)
        
        # Get sites from controller
        sites = self.controller.get_my_sites()
        
        for site in sites:
            status = self.controller.get_site_status(site['site_id'])
            
            if status:
                self.sites_tree.insert(
                    '', 'end',
                    iid=site['site_id'],  # Use full site_id as item ID
                    values=(
                        site['site_name'],
                        site['site_id'][:16] + '...',
                        status.get('state', 'Unknown'),
                        status.get('num_peers', 0),
                        f"{status.get('upload_rate', 0):.1f} KB/s"
                    )
                )

        # Restore selection
        if selected_id and self.sites_tree.exists(selected_id):
            self.sites_tree.selection_set(selected_id)
    
    def _update_downloads_list(self):
        """Update downloads list."""
        # Clear existing
        for item in self.downloads_tree.get_children():
            self.downloads_tree.delete(item)
        
        # Get downloads from controller
        downloads = self.controller.get_downloads()
        
        for download in downloads:
            self.downloads_tree.insert('', 'end', values=(
                download['site_id'][:16] + '...',
                f"{download.get('progress', 0):.1f}%",
                download.get('state', 'Unknown'),
                f"{download.get('download_rate', 0):.1f} KB/s",
                f"{download.get('upload_rate', 0):.1f} KB/s",
                download.get('num_peers', 0)
            ))
    
    def _process_log_queue(self):
        """Process log queue."""
        while not self.log_queue.empty():
            message = self.log_queue.get()
            self.log_text.insert(tk.END, message + '\n')
            self.log_text.see(tk.END)
        self.root.after(100, self._process_log_queue)

    def run(self):
        """Run the GUI."""
        self.root.mainloop()