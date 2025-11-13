"""
Main GUI application using Tkinter (cross-platform).
For production, consider migrating to PyQt5 for better UX.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from pathlib import Path
import threading
import logging
from typing import Optional

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
        self.root.geometry("900x600")
        
        # Style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Create UI
        self._create_menu()
        self._create_status_bar()
        self._create_main_content()
        
        # Start update loop
        self._update_ui()
    
    def _create_menu(self):
        """Create menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Create Site", command=self._create_site_dialog)
        file_menu.add_command(label="Import Site", command=self._import_site_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Sites menu
        sites_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Sites", menu=sites_menu)
        sites_menu.add_command(label="Add Site", command=self._add_site_dialog)
        sites_menu.add_command(label="Remove Site", command=self._remove_site)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
        help_menu.add_command(label="Terms of Service", command=self._show_terms)
    
    def _create_status_bar(self):
        """Create status bar."""
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # VPN status
        self.vpn_label = ttk.Label(
            self.status_frame,
            text="VPN: Checking...",
            foreground="orange"
        )
        self.vpn_label.pack(side=tk.LEFT, padx=5)
        
        # P2P status
        self.p2p_label = ttk.Label(
            self.status_frame,
            text="P2P: Offline",
            foreground="red"
        )
        self.p2p_label.pack(side=tk.LEFT, padx=5)
        
        # Server status
        self.server_label = ttk.Label(
            self.status_frame,
            text="Server: http://127.0.0.1:9999",
            foreground="green"
        )
        self.server_label.pack(side=tk.RIGHT, padx=5)
    
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
        # Toolbar
        toolbar = ttk.Frame(self.sites_frame)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            toolbar,
            text="Create Site",
            command=self._create_site_dialog
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            toolbar,
            text="Publish",
            command=self._publish_site
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            toolbar,
            text="Stop Seeding",
            command=self._stop_seeding
        ).pack(side=tk.LEFT, padx=2)
        
        # Sites list
        columns = ('Name', 'Site ID', 'Status', 'Peers', 'Upload')
        self.sites_tree = ttk.Treeview(
            self.sites_frame,
            columns=columns,
            show='headings'
        )
        
        for col in columns:
            self.sites_tree.heading(col, text=col)
            self.sites_tree.column(col, width=150)
        
        self.sites_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(
            self.sites_frame,
            orient=tk.VERTICAL,
            command=self.sites_tree.yview
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.sites_tree.configure(yscrollcommand=scrollbar.set)
    
    def _create_downloads_tab(self):
        """Create downloads tab."""
        # Toolbar
        toolbar = ttk.Frame(self.downloads_frame)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Label(toolbar, text="Site ID:").pack(side=tk.LEFT, padx=2)
        
        self.site_id_entry = ttk.Entry(toolbar, width=70)
        self.site_id_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            toolbar,
            text="Add Site",
            command=self._add_site_from_entry
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            toolbar,
            text="Open in Browser",
            command=self._open_site_in_browser
        ).pack(side=tk.LEFT, padx=2)
        
        # Downloads list
        columns = ('Site ID', 'Progress', 'Status', 'Down', 'Up', 'Peers')
        self.downloads_tree = ttk.Treeview(
            self.downloads_frame,
            columns=columns,
            show='headings'
        )
        
        for col in columns:
            self.downloads_tree.heading(col, text=col)
            self.downloads_tree.column(col, width=140)
        
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
            
            try:
                result = self.controller.create_site(
                    site_name,
                    Path(content_path),
                    password
                )
                
                messagebox.showinfo(
                    "Success",
                    f"Site created!\n\nSite ID:\n{result['site_id']}\n\n"
                    f"Share this ID with others to let them access your site."
                )
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create site: {e}")
        
        ttk.Button(dialog, text="Create Site", command=create).pack(pady=20)
    
    def _add_site_from_entry(self):
        """Add site from entry field."""
        site_id = self.site_id_entry.get().strip()
        if not site_id:
            messagebox.showerror("Error", "Please enter a Site ID")
            return
        
        try:
            success = self.controller.add_site(site_id)
            if success:
                messagebox.showinfo("Success", f"Site added: {site_id}")
                self.site_id_entry.delete(0, tk.END)
            else:
                messagebox.showerror("Error", "Failed to add site")
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")
    
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
        
        # TODO: Implement publish dialog
        messagebox.showinfo("Info", "Publishing... (not yet implemented)")
    
    def _stop_seeding(self):
        """Stop seeding selected site."""
        selection = self.sites_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a site")
            return
        
        # TODO: Implement stop seeding
        messagebox.showinfo("Info", "Stopped seeding")
    
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
                try:
                    if self.controller.add_site(site_id):
                        messagebox.showinfo("Success", "Site added successfully")
                        dialog.destroy()
                    else:
                        messagebox.showerror("Error", "Failed to add site")
                except Exception as e:
                    messagebox.showerror("Error", str(e))
        
        ttk.Button(dialog, text="Add", command=add).pack(pady=10)
    
    def _remove_site(self):
        """Remove selected site."""
        # TODO: Implement
        messagebox.showinfo("Info", "Not yet implemented")
    
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
            # Update VPN status
            vpn_status = self.controller.get_vpn_status()
            if vpn_status['appears_safe']:
                self.vpn_label.config(text="VPN: Active", foreground="green")
            else:
                self.vpn_label.config(text="VPN: WARNING", foreground="red")
            
            # Update P2P status
            if self.controller.is_p2p_online():
                self.p2p_label.config(text="P2P: Online", foreground="green")
            else:
                self.p2p_label.config(text="P2P: Offline", foreground="red")
            
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
        # Clear existing
        for item in self.sites_tree.get_children():
            self.sites_tree.delete(item)
        
        # Get sites from controller
        sites = self.controller.get_my_sites()
        
        for site in sites:
            status = self.controller.get_site_status(site['site_id'])
            
            if status:
                self.sites_tree.insert('', 'end', values=(
                    site['site_name'],
                    site['site_id'][:16] + '...',
                    status.get('state', 'Unknown'),
                    status.get('num_peers', 0),
                    f"{status.get('upload_rate', 0):.1f} KB/s"
                ))
    
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
    
    def run(self):
        """Run the GUI."""
        self.root.mainloop()