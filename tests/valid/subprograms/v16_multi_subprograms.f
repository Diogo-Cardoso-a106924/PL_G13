program multi
  integer a, b, c
  read *, a
  read *, b
  c = add(a, b)
  call printresult(c)
end

integer function add(x, y)
  integer x, y
  add = x + y
  return
end

subroutine printresult(n)
  integer n
  print *, n
  return
end
