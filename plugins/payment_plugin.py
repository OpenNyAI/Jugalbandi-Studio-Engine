class Plugin:

  def __init__(self):
    pass

  def process(self, CLIENT_ID: str, CLIENT_SECRET: str, mobile: str, name: str, amount: int, reason: str) -> Dict[str, Any]:

    # input validation
    
    # http call
    time.sleep(5)
    return {
      "status_code": 200,
      "transaction_id": "1234"
    }

  
