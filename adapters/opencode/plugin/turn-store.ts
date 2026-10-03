export type PendingTurn = { messageID?: string; prompt: string; admittedAt: number; consumedAt?: number }
type SessionTurns = Map<string, PendingTurn>

export class TurnStore {
  private readonly sessions = new Map<string, SessionTurns>()
  constructor(private readonly maxTurnsPerSession = 16, private readonly ttlMs = 5 * 60 * 1000) {}
  admit(sessionID: string, turn: { messageID?: string; prompt: string }, now = Date.now()): void {
    const turns = this.sessions.get(sessionID) ?? new Map<string, PendingTurn>()
    const key = turn.messageID ?? `${now}:${turn.prompt.slice(0, 32)}`
    turns.set(key, { ...turn, admittedAt: now })
    while (turns.size > this.maxTurnsPerSession) turns.delete(turns.keys().next().value as string)
    this.sessions.set(sessionID, turns)
    this.expire(now)
  }
  resolve(sessionID: string, messageID?: string): PendingTurn | undefined {
    const turns = this.sessions.get(sessionID)
    if (!turns) return undefined
    return messageID ? turns.get(messageID) : turns.values().next().value
  }
  consume(sessionID: string, messageID?: string, now = Date.now()): PendingTurn | undefined {
    const turns = this.sessions.get(sessionID)
    const key = messageID ?? turns?.keys().next().value
    if (!turns || !key) return undefined
    const turn = turns.get(key)
    if (!turn) return undefined
    turns.delete(key)
    if (!turns.size) this.sessions.delete(sessionID)
    return { ...turn, consumedAt: now }
  }
  size(sessionID: string): number { return this.sessions.get(sessionID)?.size ?? 0 }
  expire(now = Date.now()): void {
    for (const [sessionID, turns] of this.sessions) {
      for (const [key, turn] of turns) if (now - turn.admittedAt > this.ttlMs) turns.delete(key)
      if (!turns.size) this.sessions.delete(sessionID)
    }
  }
}