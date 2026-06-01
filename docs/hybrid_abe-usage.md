## Usage

### Using the Executable



The usage of the executable is as follows:
```sh
Usage: hybrid-cp-abe.exe [setup|genkey|encrypt|decrypt]
Usage: hybrid-cp-abe.exe setup <path_to_save_file>
Usage: hybrid-cp-abe.exe genkey <master_key_file> <attributes> <private_key_file>
Usage: hybrid-cp-abe.exe encrypt <public_key_file> <plaintext_file> <policy> <ciphertext_file>
Usage: hybrid-cp-abe.exe decrypt <private_key_file> <ciphertext_file> <recovertext_file>
```

Example commands:
```sh
hybrid-cp-abe.exe setup test_case
hybrid-cp-abe.exe genkey "test_case/cpabe_msk.key" "A B C" "test_case/cpabe_sk.key"
hybrid-cp-abe.exe encrypt "test_case/cpabe_pk.key" "test_case/plaintext.txt" "((A and C) or E)" "test_case/ciphertext.txt"
hybrid-cp-abe.exe decrypt "test_case/cpabe_sk.key" "test_case/ciphertext.txt" "test_case/recovertext.txt"
```