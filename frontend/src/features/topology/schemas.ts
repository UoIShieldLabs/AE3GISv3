import { z } from 'zod';
import { isIpInCidr, isValidCidr, isValidIp } from '@/utils/validation';

export const nameField = z.string().trim().min(1, 'Name is required').max(64, 'Keep it under 64 characters');

export const siteSchema = z.object({
  name: nameField,
  location: z.string().trim().max(80, 'Keep it under 80 characters'),
});
export type SiteFormValues = z.infer<typeof siteSchema>;

export const subnetSchema = z.object({
  name: nameField,
  cidr: z.string().trim().refine(isValidCidr, 'Enter a CIDR such as 10.0.1.0/24'),
});
export type SubnetFormValues = z.infer<typeof subnetSchema>;

export interface DeviceSchemaContext {
  cidr?: string;
  takenIps: string[];
  /** When editing, the device's current IP is allowed. */
  ownIp?: string;
}

export function deviceSchema(ctx: DeviceSchemaContext) {
  return z.object({
    name: nameField,
    type: z.string().min(1, 'Choose a device type'),
    image: z.string().trim().max(200),
    ip: z
      .string()
      .trim()
      .refine(isValidIp, 'Enter a valid IPv4 address')
      .refine((ip) => !ctx.cidr || isIpInCidr(ip, ctx.cidr), `Must be inside ${ctx.cidr ?? 'the subnet'}`)
      .refine((ip) => ip === ctx.ownIp || !ctx.takenIps.includes(ip), 'That IP is already used in this subnet'),
  });
}
export type DeviceFormValues = z.infer<ReturnType<typeof deviceSchema>>;

export const connectionSchema = z.object({
  label: z.string().trim().max(40),
});
