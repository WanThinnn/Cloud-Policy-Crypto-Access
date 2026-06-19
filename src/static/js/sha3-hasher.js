/**
 * SHA3-512 Pre-Hash Utility
 * 
 * Pre-hashes passwords with SHA3-512 on the client side before sending to the server.
 * The server then applies Argon2id on top of the SHA3-512 hash.
 * 
 * This ensures the plaintext password NEVER leaves the browser.
 * 
 * Requires: sha3.min.js (already loaded in base.html)
 */

/**
 * Pre-hash a password with SHA3-512.
 * @param {string} password - The plaintext password
 * @returns {string} SHA3-512 hex digest (128 characters)
 */
function prehashPassword(password) {
    if (typeof sha3_512 === 'undefined') {
        console.error('SHA3 library not loaded! Falling back to plaintext.');
        return password;
    }
    return sha3_512(password);
}
