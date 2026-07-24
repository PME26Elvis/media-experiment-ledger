import { createPrivateKey, createPublicKey } from 'node:crypto'
import { writeFile } from 'node:fs/promises'
import process from 'node:process'

const privateKeyPem = process.env.RELEASE_ED25519_PRIVATE_KEY?.trim()
const output = process.argv[2]
if (!privateKeyPem) throw new Error('RELEASE_ED25519_PRIVATE_KEY is required.')
if (!output) throw new Error('Output public key path is required.')
const privateKey = createPrivateKey(privateKeyPem)
if (privateKey.asymmetricKeyType !== 'ed25519') throw new Error(`Expected Ed25519 private key, got ${privateKey.asymmetricKeyType}.`)
const publicKey = createPublicKey(privateKey).export({ type: 'spki', format: 'pem' })
await writeFile(output, publicKey, { mode: 0o644 })
console.log(JSON.stringify({ output, keyType: 'ed25519' }))
