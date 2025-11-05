/**
 * Encryption and decryption utilities for credential storage
 * Uses Web Crypto API available in Deno
 */

import { CredentialConfig } from './types.ts';

/**
 * Get encryption key from Supabase Secrets
 * Key should be base64 encoded in the secret
 */
export function getEncryptionKey(): string {
  const key = Deno.env.get('ENCRYPTION_KEY');
  if (!key) {
    throw new Error('ENCRYPTION_KEY not found in environment variables');
  }
  return key;
}

/**
 * Encrypt data using AES-256-GCM
 * Compatible with Python's cryptography.fernet encryption
 *
 * Note: For true compatibility with Fernet, consider using a library
 * This is a simplified implementation using Web Crypto API
 */
export async function encryptJson(data: CredentialConfig): Promise<string> {
  try {
    const jsonString = JSON.stringify(data);
    const encoder = new TextEncoder();
    const dataBuffer = encoder.encode(jsonString);

    // Get key from environment
    const keyString = getEncryptionKey();
    const keyBuffer = encoder.encode(keyString);

    // Import key for AES-GCM
    const key = await crypto.subtle.importKey(
      'raw',
      await crypto.subtle.digest('SHA-256', keyBuffer),
      { name: 'AES-GCM', length: 256 },
      false,
      ['encrypt']
    );

    // Generate random IV
    const iv = crypto.getRandomValues(new Uint8Array(12));

    // Encrypt data
    const encryptedBuffer = await crypto.subtle.encrypt(
      { name: 'AES-GCM', iv },
      key,
      dataBuffer
    );

    // Combine IV and encrypted data
    const combined = new Uint8Array(iv.length + encryptedBuffer.byteLength);
    combined.set(iv, 0);
    combined.set(new Uint8Array(encryptedBuffer), iv.length);

    // Convert to base64
    return btoa(String.fromCharCode(...combined));
  } catch (error) {
    throw new Error(`Encryption failed: ${error.message}`);
  }
}

/**
 * Decrypt encrypted data
 */
export async function decryptJson(encryptedText: string): Promise<CredentialConfig> {
  try {
    const encoder = new TextEncoder();
    const decoder = new TextDecoder();

    // Get key from environment
    const keyString = getEncryptionKey();
    const keyBuffer = encoder.encode(keyString);

    // Import key for AES-GCM
    const key = await crypto.subtle.importKey(
      'raw',
      await crypto.subtle.digest('SHA-256', keyBuffer),
      { name: 'AES-GCM', length: 256 },
      false,
      ['decrypt']
    );

    // Decode base64
    const combined = Uint8Array.from(atob(encryptedText), c => c.charCodeAt(0));

    // Extract IV and encrypted data
    const iv = combined.slice(0, 12);
    const encryptedBuffer = combined.slice(12);

    // Decrypt data
    const decryptedBuffer = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv },
      key,
      encryptedBuffer
    );

    // Convert to string and parse JSON
    const jsonString = decoder.decode(decryptedBuffer);
    return JSON.parse(jsonString);
  } catch (error) {
    throw new Error(`Decryption failed: ${error.message}`);
  }
}

/**
 * Alternative: Use Fernet-compatible encryption
 * This is a placeholder for a more robust implementation
 *
 * For production, consider using a library like:
 * - https://deno.land/x/fernet
 * - Or implement full Fernet spec: https://github.com/fernet/spec/blob/master/Spec.md
 */
export class FernetEncryption {
  private key: Uint8Array;

  constructor(keyString?: string) {
    const key = keyString || getEncryptionKey();
    // Decode base64 key
    this.key = Uint8Array.from(atob(key), c => c.charCodeAt(0));
  }

  /**
   * Encrypt using Fernet format (placeholder)
   */
  async encrypt(data: string): Promise<string> {
    // TODO: Implement full Fernet encryption
    // For now, use simple AES-GCM
    const config = JSON.parse(data) as CredentialConfig;
    return await encryptJson(config);
  }

  /**
   * Decrypt Fernet token (placeholder)
   */
  async decrypt(token: string): Promise<string> {
    // TODO: Implement full Fernet decryption
    // For now, use simple AES-GCM
    const config = await decryptJson(token);
    return JSON.stringify(config);
  }
}

/**
 * Validate encryption key format
 */
export function validateEncryptionKey(key: string): boolean {
  try {
    // Key should be base64 encoded
    atob(key);
    return true;
  } catch {
    return false;
  }
}

/**
 * Generate a random encryption key (for setup/testing)
 */
export function generateEncryptionKey(): string {
  const key = crypto.getRandomValues(new Uint8Array(32));
  return btoa(String.fromCharCode(...key));
}
