import pefile

pe_path = r"F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_family.exe"
pe = pefile.PE(pe_path)

image_base = pe.OPTIONAL_HEADER.ImageBase
print(f"ImageBase: 0x{image_base:08X}")
print(f"PE file: {pe_path}")
print("=" * 90)

# Target functions
targets = {
    "CreateFileA", "WriteFile", "CloseHandle",
    "ReadFile", "OpenFile", "lcreat", "lclose", "_lcreat", "_lclose",
    "CreateFileW", "WriteFileEx", "ReadFileEx",
    "SetFilePointer", "GetFileSize", "DeleteFileA", "DeleteFileW",
    "MoveFileA", "MoveFileW", "CopyFileA", "CopyFileW",
    "GetFileAttributesA", "GetFileAttributesW",
    "FindFirstFileA", "FindNextFileA", "FindClose",
    "FlushFileBuffers", "SetEndOfFile",
    "LockFile", "UnlockFile",
    "GetFileType", "SetFileAttributesA",
}

print("\n--- ALL IMPORTS WITH IAT ADDRESSES ---\n")

all_imports = []

if hasattr(pe, 'DIRECTORY_ENTRY_IMPORT'):
    for entry in pe.DIRECTORY_ENTRY_IMPORT:
        dll_name = entry.dll.decode('utf-8', errors='replace')
        print(f"\nDLL: {dll_name}")
        print(f"  {'Function':<40} {'Hint':<8} {'IAT (VA)':<14} {'IAT (RVA)':<14}")
        print(f"  {'-'*40} {'-'*8} {'-'*14} {'-'*14}")
        
        for imp in entry.imports:
            func_name = imp.name.decode('utf-8', errors='replace') if imp.name else f"Ordinal#{imp.ordinal}"
            iat_va = imp.address  # This is the VA where the function pointer is stored
            iat_rva = iat_va - image_base if iat_va >= image_base else iat_va
            
            is_target = "  <<<" if func_name in targets else ""
            print(f"  {func_name:<40} {imp.hint:<8} 0x{iat_va:08X}   0x{iat_rva:08X}{is_target}")
            
            all_imports.append((dll_name, func_name, iat_va, iat_rva))

print("\n" + "=" * 90)
print("\n--- TARGET FUNCTION SUMMARY ---\n")

found_targets = []
for dll_name, func_name, iat_va, iat_rva in all_imports:
    if func_name in targets:
        found_targets.append((dll_name, func_name, iat_va, iat_rva))

if found_targets:
    for dll_name, func_name, iat_va, iat_rva in found_targets:
        print(f"  {func_name:<25} from {dll_name:<25} IAT VA: 0x{iat_va:08X}   RVA: 0x{iat_rva:08X}")
else:
    print("  No target functions found in imports!")

# Also check if there are any file-related functions we might have missed
print("\n--- FILE-RELATED API CHECK ---\n")
file_keywords = ['file', 'creat', 'close', 'write', 'read', 'open', 'delete', 'move', 'copy', 'flush', 'lock', 'unlock', 'handle', 'directory', 'find', 'path', 'volume']
for dll_name, func_name, iat_va, iat_rva in all_imports:
    func_lower = func_name.lower()
    if any(kw in func_lower for kw in file_keywords):
        marker = " [TARGET]" if func_name in targets else ""
        print(f"  {func_name:<40} from {dll_name:<25} IAT VA: 0x{iat_va:08X}{marker}")

pe.close()
