import { DocumentData } from './types';

export const PTO_POLICY_DATA: DocumentData = {
  root: {
    id: "root",
    label: "",
    title: "Paid Time Off Policy",
    text: "seed",
    depth: 0,
    children: [
      {
        id: "1-aacd31",
        label: "1",
        title: "Scope",
        text: "This policy applies to all regular full-time and part-time employees.\n\nContractors and interns are covered by separate arrangements.",
        depth: 1,
        children: []
      },
      {
        id: "2-7fef72",
        label: "2",
        title: "Accrual",
        text: "Paid time off accrues monthly and is credited on the last day of each month.",
        depth: 1,
        children: [
          {
            id: "2.1-799af0",
            label: "2.1",
            title: "Accrual rates",
            text: "Rates vary by length of service, as set out below.\n\nYears of service | Days per year\n0-2 | 15\n3 or more | 20",
            depth: 2,
            children: []
          },
          {
            id: "2.2-520442",
            label: "2.2",
            title: "Carryover",
            text: "Unused days may be carried into the following calendar year, subject to the limits below.",
            depth: 2,
            children: [
              {
                id: "2.2.(a)-ec5926",
                label: "(a)",
                title: "Standard limit",
                text: "A maximum of 10 accrued days may be carried over.",
                depth: 3,
                children: []
              },
              {
                id: "2.2.(b)-718ee4",
                label: "(b)",
                title: "Forfeiture",
                text: "Days in excess of the carryover limit are forfeited on December 31.",
                depth: 3,
                children: []
              }
            ]
          }
        ]
      },
      {
        id: "3-e79dd8",
        label: "3",
        title: "Requesting leave",
        text: "Requests must be submitted through the employee portal at least 14 days in advance.",
        depth: 1,
        children: []
      }
    ]
  }
};

export const CONTRACT_AGREEMENT_DATA: DocumentData = {
  root: {
    id: "root",
    label: "",
    title: "Master Services Agreement",
    text: "This Master Services Agreement is entered into between Client and Provider as of the Effective Date.",
    depth: 0,
    children: [
      {
        id: "1-b72e19",
        label: "1",
        title: "Definitions and Interpretation",
        text: "The terms used in this Agreement shall have the meanings attributed to them in this Section 1 unless context dictates otherwise.",
        depth: 1,
        children: [
          {
            id: "1.1-9a31bc",
            label: "1.1",
            title: "Applicable Laws",
            text: "Means all statutes, ordinances, regulations, and orders of any governmental authority.",
            depth: 2,
            children: []
          },
          {
            id: "1.2-d38a22",
            label: "1.2",
            title: "Deliverables",
            text: "All outputs, reports, code, and documentation generated during the provision of Services.",
            depth: 2,
            children: []
          }
        ]
      },
      {
        id: "2-c841aa",
        label: "2",
        title: "Obligations of the Parties",
        text: "Each party shall perform its obligations in good faith and with reasonable diligence.",
        depth: 1,
        children: [
          {
            id: "2.1-ef1240",
            label: "2.1",
            title: "Performance Standards",
            text: "Provider shall render services adhering to highest industry standards.",
            depth: 2,
            children: []
          }
        ]
      }
    ]
  }
};

export const BLANK_DATA: DocumentData = {
  root: {
    id: "root",
    label: "",
    title: "Untitled Document",
    text: "Enter document preface or introduction...",
    depth: 0,
    children: [
      {
        id: "1-100001",
        label: "1",
        title: "Introduction",
        text: "Write your introductory section here.",
        depth: 1,
        children: []
      }
    ]
  }
};
