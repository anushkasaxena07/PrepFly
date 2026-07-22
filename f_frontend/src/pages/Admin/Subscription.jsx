import React from 'react';
import SubscriptionComponent from '../../components/subscription/Subscription';
import { adminFetch } from '../../services/adminAPI';

export default function Subscription() {
  const userObj = JSON.parse(localStorage.getItem("admin_user") || localStorage.getItem("user") || "{}");
  const orgId = localStorage.getItem("admin_org_id") || userObj.organization_id || "d258e381-6a6e-4376-8bf2-2865731b1939";

  return <SubscriptionComponent apiFetch={adminFetch} orgId={orgId} isAdmin={true} />;
}
