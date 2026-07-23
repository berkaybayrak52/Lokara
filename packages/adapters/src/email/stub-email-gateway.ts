import type { EmailDeliveryReceipt, EmailGateway, OutgoingEmail } from './email-gateway';

/**
 * Dev/test stub: records sends in memory instead of delivering.
 * TODO(provider): real EU provider adapter at M9 (SPF/DKIM/DMARC on @lokaraimmo.de).
 */
export class StubEmailGateway implements EmailGateway {
  readonly sent: Array<{ email: OutgoingEmail; receipt: EmailDeliveryReceipt }> = [];
  private counter = 0;

  send(email: OutgoingEmail): Promise<EmailDeliveryReceipt> {
    this.counter += 1;
    const receipt: EmailDeliveryReceipt = {
      messageId: `stub-msg-${this.counter}`,
      status: 'QUEUED',
      acceptedAt: new Date().toISOString(),
    };
    this.sent.push({ email, receipt });
    return Promise.resolve(receipt);
  }
}
