import "server-only";

const LENDERS = [
  {
    clientId: "lender-a",
    name: "Lender A",
    secretVar: "LENDER_A_SECRET",
  },
  {
    clientId: "lender-b",
    name: "Lender B",
    secretVar: "LENDER_B_SECRET",
  },
];

export const getLender = (clientId: string) => {
  const lender = LENDERS.find((item) => item.clientId === clientId);

  if (!lender) {
    return null;
  }

  const secret = process.env[lender.secretVar];

  if (!secret) {
    throw new Error(`${lender.secretVar} not set`);
  } else {
    return { ...lender, secret };
  }
};
