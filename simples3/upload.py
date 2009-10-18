"""HTML & Flash uploading to S3"""

try:
    import json
except ImportError:
    import simplejson as json

from .bucket import iso8601_fmt, _iso8601_dt

class S3UploadPolicy(dict):
    @property
    def expiration(self):
        return _iso8601_dt(self["expiration"])
    @expiration.setter
    def expiration(self, value):
        self["expiration"] = value.strftime(iso8601_fmt)
    @expiration.deleter
    def expiration(self):
        del self["expiration"]

    def restrict(self, **conds):
        for cond, value in conds.iteritems():
            cond_tp = None
            if "__" in cond:
                cond_var, cond_tp = cond.rsplit("__", 1)
            else:
                cond_var = cond

            if cond_var == "size":
                cond_var = "content-length-range"
            elif cond_var == "success_url":
                cond_var = "success_action_redirect"
            elif cond_var == "success_status":
                cond_var = "success_action_status"

            if cond_tp == "startswith":
                cond_tp_nam = "starts-with"
            elif cond_tp == "exact":
                cond_tp_nam = "eq"
            elif cond_tp == "between":
                cond_tp_nam = "range"
            elif cond_tp is None:
                cond_tp_nam = None
            else:
                raise ValueError("%s is not a valid condition" % cond_tp)

            if cond_tp_nam == "range":
                rng_min, rng_max = value
                cond_val = [cond_var, int(rng_min), int(rng_max)]
            elif cond_tp_nam is not None:
                cond_val = [cond_tp_nam, "$" + cond_var, value]
            else:
                cond_val = {cond_var: value}
            self.setdefault("conditions", []).append(cond_val)

    def encode(self):
        """Encode policy as a Base64-encoded JSON string."""
        return json.dumps(self).encode("base64")[:-1]

class S3UploadForm(object):
    """AWS S3 HTML upload form helper"""

    # TODO DevPay stuff?

    def __init__(self, key, acl, policy=None, metadata={}, signer=None,
                 success_url=None, success_status=None):
        if success_url and success_status:
            raise ValueError("specify either success_url or success_status")
        self.key = key
        self.acl = acl
        self.metadata = metadata
        self.signer = signer
        self.success_url = success_url
        if success_status:
            self.success_status = success_status
        elif not success_url:
            self.success_status = 204
        else:
            self.success_status = None
        # Set up a sane default policy
        self.policy = S3UploadPolicy()
        self.policy.restrict(acl=acl)
        if self.success_url:
            self.policy.restrict(success_url=self.success_url)
        elif self.success_status:
            self.policy.restrict(success_status=str(self.success_status))
        if key.endswith("${filename}"):
            self.policy.restrict(key__startswith=key[:-11])
        elif "${filename}" not in key:
            self.policy.restrict(key=key)
        # Merge user-specified policy
        for k, v in policy.iteritems():
            if k == "conditions":
                self.policy["conditions"].extend(v)
            else:
                self.policy[k] = v

    @property
    def signature(self):
        """Signature string for the policy."""
        if not self.policy:
            raise ValueError("cannot sign empty policy")
        elif not self.signer:
            raise TypeError("self.signer is not set")
        return self.signer(self.policy.encode())

    def bind_to_bucket(self, bucket):
        """Bind the S3 upload form to *bucket*.

        This really only makes the signature generator use *bucket*, and adds a
        constraint to the policy which says that only *bucket* can be used.
        """
        if self.signer:
            raise TypeError("cannot bind to a bucket when a signer is set")
        self.signer = bucket.sign_description
        self.policy.restrict(bucket=bucket.name)
