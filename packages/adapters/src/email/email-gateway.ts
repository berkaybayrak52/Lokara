/**
 * Port for compliance-grade transactional email (Modell A: own domain,
 * From-name = landlord). Delivery states feed the append-only EmailDelivery
 * ledger and the 3-colour Zustell-Ampel (§556 proof of receipt) at M9.
 * TODO(provider): EU provider (SES Frankfurt / Postmark / Brevo) chosen at M9.
 */
export type DeliveryStatus = 'QUEUED' | 'DELIVERED' | 'BOUNCED';

export interface OutgoingEmail {
  readonly to: string;
  readonly fromName: string;
  readonly subject: string;
  readonly htmlBody: string;
}

export interface EmailDeliveryReceipt {
  readonly messageId: string;
  readonly status: DeliveryStatus;
  readonly acceptedAt: string;
}

export interface EmailGateway {
  send(email: OutgoingEmail): Promise<EmailDeliveryReceipt>;
}
