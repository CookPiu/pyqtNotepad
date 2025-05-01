import os, re, shutil, yaml

class FileClassifier:
    def __init__(self, rules_path="classify_rules.yaml"):
        """Initializes the classifier with rules from the YAML file."""
        try:
            with open(rules_path, 'r', encoding="utf-8") as f:
                self.rules = yaml.safe_load(f)
            if not isinstance(self.rules, dict):
                 raise ValueError("Rules file is not a valid dictionary.")
        except FileNotFoundError:
            print(f"[WARN] Classifier: Rules file not found at '{rules_path}'. Classification might be limited to 'Others'.")
            self.rules = {} # Empty rules
        except Exception as e:
             print(f"[ERROR] Classifier: Failed to load or parse rules from '{rules_path}': {e}")
             self.rules = {}

        # Load rules safely, providing empty dicts as defaults
        self.type_map    = self.rules.get("type_map", {})
        self.keyword_map = self.rules.get("keyword_map", {})
        self.regex_map   = self.rules.get("regex_map", {})
        self.default     = self.rules.get("default", "Others")

        # Store all known target category folder names for quick lookup
        self.category_folders = set(self.keyword_map.keys()) | \
                                set(self.regex_map.keys()) | \
                                set(self.type_map.keys()) | \
                                {self.default}

        # Convert keywords to lowercase only once for efficiency
        self.keyword_map_lower = {cat: [kw.lower() for kw in kws]
                                  for cat, kws in self.keyword_map.items()}

    def get_category_for_file(self, filename):
        """
        Determines the target category for a filename based on rules.
        Priority: Keyword -> Regex -> Type -> Default.
        Returns the category name (string).
        """
        lower_fname = filename.lower()
        target_category = None

        # 1. Keyword Match (case-insensitive)
        for cat, lower_kws in self.keyword_map_lower.items():
            if any(kw in lower_fname for kw in lower_kws):
                target_category = cat
                break
        if target_category:
            # print(f"[Debug] Classified '{filename}' as '{target_category}' by keyword.")
            return target_category

        # 2. Regex Match (case-insensitive)
        for cat, pat in self.regex_map.items():
            try:
                if re.search(pat, filename, re.IGNORECASE):
                    target_category = cat
                    break
            except re.error as re_err:
                 print(f"    [WARN] Invalid regex pattern for category '{cat}': {pat} - {re_err}")
                 continue # Skip this pattern
        if target_category:
            # print(f"[Debug] Classified '{filename}' as '{target_category}' by regex.")
            return target_category

        # 3. Type Match (case-insensitive extension)
        ext = os.path.splitext(filename)[1].lower()
        for cat, exts in self.type_map.items():
            # Ensure exts is iterable, default to empty list if missing/None
            if ext in (exts or []):
                target_category = cat
                break
        if target_category:
            # print(f"[Debug] Classified '{filename}' as '{target_category}' by type.")
            return target_category

        # 4. Default Category ('Others')
        # print(f"[Debug] Classified '{filename}' as default '{self.default}'.")
        return self.default

    # --- Methods for manual recursive classification (Not used in default flow anymore) ---

    def classify_directory_recursively(self, root_dir):
        """
        (Manual Use) Recursively walks through root_dir and moves files
        found outside their designated category subfolder into the correct one.
        Useful for a one-time cleanup or if triggered by a specific command.
        """
        print(f"  [Classifier] Starting MANUAL recursive classification in: '{os.path.basename(root_dir)}'")
        moved_count = 0
        skipped_count = 0
        error_count = 0

        for dirpath, dirnames, filenames in os.walk(root_dir, topdown=True):
            relative_dirpath = os.path.relpath(dirpath, root_dir)
            path_parts = relative_dirpath.replace('\\', '/').split('/')

            # Skip processing if already inside a known category folder relative to root_dir
            if relative_dirpath != '.' and path_parts[0] in self.category_folders:
                dirnames[:] = [] # Don't recurse further into category folders
                continue

            for fname in filenames:
                src_path = os.path.join(dirpath, fname)
                try:
                    # Determine category without moving first
                    target_category = self.get_category_for_file(fname)
                    # Try to move if category determined and not already correct
                    moved = self._move_file_if_needed(src_path, root_dir, target_category)

                    if moved is True:
                        moved_count += 1
                    elif moved is False:
                         skipped_count += 1
                except Exception as e:
                    print(f"    [ERROR] Classifier: Error classifying/moving file '{fname}': {e}")
                    error_count += 1

        print(f"  [Classifier] Finished MANUAL classification in '{os.path.basename(root_dir)}'. Moved: {moved_count}, Skipped: {skipped_count}, Errors: {error_count}")


    def _move_file_if_needed(self, src_path, base_target_dir, category):
        """
        (Helper for manual classification) Moves the source file to the target
        category directory under base_target_dir, but only if it's not already there.
        Returns True if moved, False if skipped or error.
        """
        src_dir = os.path.dirname(src_path)
        src_filename = os.path.basename(src_path)

        # Calculate relative path of source directory
        try:
             relative_src_dir = os.path.relpath(src_dir, base_target_dir)
        except ValueError:
             relative_src_dir = None # Should not happen in os.walk context

        # Check if the file is already in the correct category folder relative to base_target_dir
        if relative_src_dir is not None and relative_src_dir.replace('\\', '/') == category:
            return False # Already in the right place

        dst_dir = os.path.join(base_target_dir, category)
        dst_path = os.path.join(dst_dir, src_filename)

        # Create destination directory
        os.makedirs(dst_dir, exist_ok=True)

        # Check for existing destination file
        if os.path.exists(dst_path):
            print(f"    [WARN] File '{src_filename}' already exists in target category '{category}'. Skipping move.")
            # Add hash comparison here if needed for overwrite logic
            return False # Skip move

        # Perform the move
        try:
            source_description = f"'{os.path.basename(src_dir)}'" if relative_src_dir != '.' else "'root'"
            print(f"    [MOVE] '{src_filename}' from {source_description} → '{category}'")
            shutil.move(src_path, dst_path)
            return True # Moved successfully
        except Exception as e:
            print(f"    [ERROR] Failed to move '{src_filename}' to '{dst_dir}': {e}")
            return False # Move failed
